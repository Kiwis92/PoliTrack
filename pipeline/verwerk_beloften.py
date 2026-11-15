#!/usr/bin/env python3
"""Koppelt opgehaalde stemmingen aan beloften en rekent de inzetscore uit.

Invoer
------
beloften/<id>.json        Vooraf vastgelegde belofte: zoektermen, dossiers, periode.
                          Bestanden die met een underscore beginnen worden overgeslagen.
beoordelingen/<id>/codering-<naam>.json
                          Onafhankelijke codering per codeur ("ai" of een GitHub-naam).
beoordelingen/<id>/beslissingen.json
                          Eindbeslissing bij stemmingen waar de codeurs verschillen.
resultaten/<id>.json      Geaccordeerd resultaatoordeel (is de belofte gerealiseerd).
data/besluiten/           Opgehaalde stemmingen (zie sync_stemmingen.py).

Uitvoer (wordt elke run opnieuw gemaakt, niet met de hand aanpassen)
------
data/kandidaten/<id>.json   Het zoekuniversum: alle stemmingen die mechanisch matchen.
data/scores/<id>.json       Inzetscore volgens methode v2, plus het resultaatoordeel.
data/beoordelingsrij.json   Overzicht: hoeveel kandidaten per belofte nog wachten.
data/betrouwbaarheid.json   Overeenstemming tussen codeurs (Cohen's kappa).

Dubbele codering: een stemming telt pas mee als minstens twee codeurs haar
onafhankelijk hebben gecodeerd. Zijn ze het eens over opname en richting, dan
is dat de uitkomst. Verschillen ze, dan is een beslissing nodig.

De selectie is mechanisch: een stemming is kandidaat als de zaak een wet,
amendement of motie is, de stemdatum in de periode valt, en een zoekterm in
titel of onderwerp voorkomt of de zaak in een vastgelegd dossier valt.
Of een kandidaat meetelt en in welke richting, beslist een mens.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from tijdlijn import Tijdlijn

ROOT = Path(__file__).resolve().parent.parent
BELOFTEN = ROOT / "beloften"
BEOORDELINGEN = ROOT / "beoordelingen"
RESULTATEN = ROOT / "resultaten"
DATA = ROOT / "data"
TIJDLIJN = ROOT / "tijdlijn"

# Zaaksoort uit de API -> type in de methode
TYPE = {
    "Motie": "motie",
    "Amendement": "amendement",
    "Wetgeving": "wet",
    "Initiatiefwetgeving": "wet",
    "Begroting": "wet",
}
GEWICHT = {"wet": 5.0, "amendement": 3.0, "motie": 1.0}
GEWICHT_ONDERZOEKSMOTIE = 0.5
MIN_BEWIJS = 3.0
BANDEN = [(0.80, "Consistent"), (0.60, "Overwegend consistent"), (0.40, "Gemengd"), (0.0, "Strijdig")]
REDEN_CODES = {"U1", "U2", "U3", "U4"}
RICHTINGEN = {"voor_belofte", "tegen_belofte"}
RESULTAAT_WAARDE = {"gerealiseerd": 1.0, "deels_gerealiseerd": 0.5, "niet_gerealiseerd": 0.0}
RESULTAAT_OVERIG = {"loopt_nog", "niet_toetsbaar"}


def lees_json(pad: Path):
    return json.loads(pad.read_text(encoding="utf-8"))


def schrijf_json(pad: Path, inhoud) -> None:
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(json.dumps(inhoud, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def band(score: float) -> str:
    for grens, naam in BANDEN:
        if score >= grens:
            return naam
    return BANDEN[-1][1]


def lees_besluiten() -> list[dict]:
    map_ = DATA / "besluiten"
    if not map_.exists():
        return []
    return [lees_json(p) for p in sorted(map_.glob("*/*.json"))]


def partijstem(besluit: dict, fracties: set[str]) -> dict:
    """Telt de stemmen van de partij. Fractiestemming telt met fractiegrootte,
    hoofdelijke stemming telt per persoon."""
    telling = {"voor": 0, "tegen": 0, "niet_deelgenomen": 0, "vergissing": False}
    for s in besluit["stemmingen"]:
        if (s.get("fractie") or "").lower() not in fracties:
            continue
        aantal = 1 if s.get("persoon_id") else (s.get("fractiegrootte") or 1)
        sleutel = {"Voor": "voor", "Tegen": "tegen"}.get(s.get("stem"), "niet_deelgenomen")
        telling[sleutel] += aantal
        telling["vergissing"] = telling["vergissing"] or bool(s.get("vergissing"))
    return telling


def zoek_kandidaten(belofte: dict, besluiten: list[dict], tijdlijn: Tijdlijn | None = None) -> list[dict]:
    tijdlijn = tijdlijn or Tijdlijn(TIJDLIJN)
    termen = [t.lower() for t in belofte.get("zoektermen", [])]
    dossiers = {str(d) for d in belofte.get("dossiers", [])}
    van, tot = belofte.get("periode_van") or "", belofte.get("periode_tot") or "9999"
    vaste_fracties = {f.lower() for f in belofte.get("fracties") or []}
    kandidaten = []
    for b in besluiten:
        dag = (b.get("datum") or "")[:10]
        if not dag or not (van <= dag <= tot):
            continue
        # Fractienamen volgen de tijdlijn (fusies, naamswijzigingen); een vaste lijst in de belofte gaat voor.
        fracties = vaste_fracties or tijdlijn.fracties_op(belofte["partij"], dag)
        if not fracties:
            continue
        positie = tijdlijn.positie_op(belofte["partij"], dag)
        for z in b["zaken"]:
            type_ = TYPE.get(z.get("soort"))
            if not type_:
                continue
            tekst = f"{z.get('titel') or ''} {z.get('onderwerp') or ''}".lower()
            treffers = [t for t in termen if t in tekst]
            # Een dossier "21501" matcht ook subdossier "21501-30".
            dossier_treffers = sorted(
                d for d in z.get("dossiers", []) if d in dossiers or d.split("-")[0] in dossiers
            )
            if not treffers and not dossier_treffers:
                continue
            stem = partijstem(b, fracties)
            if stem["voor"] + stem["tegen"] + stem["niet_deelgenomen"] == 0:
                continue  # partij zat niet in de Kamer of stemde niet mee
            dossier = (z.get("dossiers") or ["geen-dossier"])[0]
            kandidaten.append(
                {
                    "sleutel": f"{b['besluit_id']}:{z['id']}",
                    "datum": dag,
                    "zaaknummer": z.get("nummer"),
                    "type": type_,
                    "titel": z.get("titel"),
                    "onderwerp": z.get("onderwerp"),
                    "dossiers": z.get("dossiers", []),
                    "besluit": b.get("besluittekst"),
                    "stemmingssoort": b.get("stemmingssoort"),
                    "partijstem": stem,
                    "fracties": sorted(fracties),
                    "positie": positie["positie"],
                    "kabinet": positie["kabinet"],
                    "demissionair": positie["demissionair"],
                    "cluster": f"{dossier}|{dag}|{type_}",
                    "treffer_zoektermen": treffers,
                    "treffer_dossiers": dossier_treffers,
                }
            )
    kandidaten.sort(key=lambda k: (k["datum"], k["zaaknummer"] or "", k["sleutel"]))
    return kandidaten


def reken_inzet(items: list[dict]) -> dict | None:
    """items: opgenomen stemmingen met type, cluster, c, d, onderzoeksmotie."""
    if not items:
        return None
    per_cluster = defaultdict(int)
    for it in items:
        per_cluster[it["cluster"]] += 1
    teller = noemer = 0.0
    ruw_consistent = 0.0
    for it in items:
        t = GEWICHT_ONDERZOEKSMOTIE if (it["type"] == "motie" and it["onderzoeksmotie"]) else GEWICHT[it["type"]]
        it["w"] = round(t * it["d"] / per_cluster[it["cluster"]], 4)
        teller += it["w"] * it["c"]
        noemer += it["w"]
        ruw_consistent += it["c"]
    if noemer == 0:
        return None
    return {
        "score": round(teller / noemer, 3),
        "som_gewichten": round(noemer, 3),
        "ruw_consistent": round(ruw_consistent, 2),
        "ruw_totaal": len(items),
    }


def categorie(codering: dict) -> str | None:
    """Waar codeurs het over eens moeten zijn: uitsluiten, of de richting."""
    if codering.get("opname") is False:
        return "uitsluiten"
    if codering.get("opname") is True and codering.get("richting_voorstem") in RICHTINGEN:
        return codering["richting_voorstem"]
    return None


def lees_coderingen(belofte_id: str) -> tuple[dict, dict]:
    """Geeft ({codeur: {sleutel: codering}}, beslissingen) terug."""
    map_ = BEOORDELINGEN / belofte_id
    coderingen = {}
    if map_.exists():
        for pad in sorted(map_.glob("codering-*.json")):
            inhoud = lees_json(pad)
            naam = inhoud.get("codeur") or pad.stem.removeprefix("codering-")
            coderingen[naam] = {
                k: v for k, v in (inhoud.get("coderingen") or {}).items() if categorie(v)
            }
    beslis_pad = map_ / "beslissingen.json"
    beslissingen = lees_json(beslis_pad) if beslis_pad.exists() else {}
    return coderingen, {k: v for k, v in beslissingen.items() if not k.startswith("_")}


def bepaal_definitief(kandidaten: list[dict], coderingen: dict, beslissingen: dict) -> tuple[dict, dict]:
    """Past de regel van dubbele codering toe.

    Geeft (definitief, stand) terug. stand telt per status hoeveel kandidaten
    er zijn: ongecodeerd, een_codering, geschil, definitief."""
    # Een mens gaat voor bij de details (directheid, toelichting); AI staat achteraan.
    volgorde = sorted(coderingen, key=lambda n: (n == "ai", n))
    definitief, stand = {}, {"ongecodeerd": 0, "een_codering": 0, "geschil": 0, "definitief": 0}
    for k in kandidaten:
        sleutel = k["sleutel"]
        gegeven = [coderingen[n][sleutel] for n in volgorde if sleutel in coderingen[n]]
        if sleutel in beslissingen and categorie(beslissingen[sleutel]):
            definitief[sleutel] = beslissingen[sleutel]
            stand["definitief"] += 1
        elif len(gegeven) < 2:
            stand["ongecodeerd" if not gegeven else "een_codering"] += 1
        elif len({categorie(c) for c in gegeven}) == 1:
            definitief[sleutel] = gegeven[0]
            stand["definitief"] += 1
        else:
            stand["geschil"] += 1
    return definitief, stand


def kappa(paren: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa over paren (categorie codeur A, categorie codeur B)."""
    n = len(paren)
    if n == 0:
        return None
    eens = sum(1 for a, b in paren if a == b) / n
    labels = {x for paar in paren for x in paar}
    kans = sum(
        (sum(1 for a, _ in paren if a == l) / n) * (sum(1 for _, b in paren if b == l) / n)
        for l in labels
    )
    if kans == 1:
        return 1.0
    return round((eens - kans) / (1 - kans), 3)


def codeurparen(coderingen: dict) -> dict:
    """Voor elk tweetal codeurs: de paren categorieën op gezamenlijk gecodeerde stemmingen."""
    namen = sorted(coderingen)
    uit = {}
    for i, a in enumerate(namen):
        for b in namen[i + 1 :]:
            samen = sorted(set(coderingen[a]) & set(coderingen[b]))
            if samen:
                uit[f"{a} / {b}"] = [
                    (categorie(coderingen[a][s]), categorie(coderingen[b][s])) for s in samen
                ]
    return uit


def lees_resultaat(belofte_id: str) -> dict:
    pad = RESULTATEN / f"{belofte_id}.json"
    if not pad.exists():
        return {"oordeel": None, "status": "nog niet geaccordeerd"}
    r = lees_json(pad)
    oordeel = r.get("oordeel")
    if oordeel not in RESULTAAT_WAARDE and oordeel not in RESULTAAT_OVERIG:
        return {"oordeel": None, "status": f"ongeldig oordeel: {oordeel}"}
    uit = {
        "oordeel": oordeel,
        "waarde": RESULTAAT_WAARDE.get(oordeel),
        "vlaggen": r.get("vlaggen", []),
        "toelichting": r.get("toelichting"),
        "bronnen": r.get("bronnen", []),
        "geaccordeerd_door": r.get("door"),
        "geaccordeerd_op": r.get("op"),
        "status": "geaccordeerd",
    }
    if oordeel == "niet_gerealiseerd" and not r.get("wederhoor"):
        uit["status"] = "wacht op wederhoor"
    return uit


def bereken_score(belofte: dict, kandidaten: list[dict], beoordeling: dict) -> dict:
    items, fouten, uitgesloten, open_ = [], [], [], []
    for k in kandidaten:
        oordeel = beoordeling.get(k["sleutel"])
        if not oordeel or oordeel.get("opname") is None:
            open_.append(k["sleutel"])
            continue
        if oordeel["opname"] is False:
            code = oordeel.get("reden_code")
            if code not in REDEN_CODES:
                fouten.append(f"{k['sleutel']}: uitsluiting zonder geldige reden_code (U1-U4)")
            uitgesloten.append({"sleutel": k["sleutel"], "zaaknummer": k["zaaknummer"], "reden_code": code})
            continue
        richting, d = oordeel.get("richting_voorstem"), oordeel.get("directheid", 1)
        if richting not in RICHTINGEN or d not in (1, 0.5):
            fouten.append(f"{k['sleutel']}: richting_voorstem of directheid ontbreekt of is ongeldig")
            continue
        stem = k["partijstem"]
        deelgenomen = stem["voor"] + stem["tegen"]
        if deelgenomen == 0:
            uitgesloten.append({"sleutel": k["sleutel"], "zaaknummer": k["zaaknummer"], "reden_code": "niet deelgenomen"})
            continue
        consistent = stem["voor"] if richting == "voor_belofte" else stem["tegen"]
        items.append(
            {
                "sleutel": k["sleutel"],
                "datum": k["datum"],
                "zaaknummer": k["zaaknummer"],
                "type": k["type"],
                "titel": k["titel"],
                "onderwerp": k["onderwerp"],
                "besluit": k["besluit"],
                "positie": k.get("positie", "onbekend"),
                "richting_voorstem": richting,
                "cluster": k["cluster"],
                "c": round(consistent / deelgenomen, 4),
                "d": d,
                "onderzoeksmotie": bool(oordeel.get("onderzoeksmotie")),
                "coalitiediscipline": bool(oordeel.get("coalitiediscipline")),
            }
        )
    resultaat = {
        "belofte_id": belofte["id"],
        "methode": "v2",
        "opgenomen": items,
        "uitgesloten": uitgesloten,
        "nog_te_beoordelen": len(open_),
        "fouten": fouten,
    }
    fasen = Tijdlijn.fasen(items)
    posities = [f["positie"] for f in fasen]
    resultaat["positie"] = posities[0] if len(set(posities)) == 1 else "wisselend"
    if len(set(posities)) > 1:
        # Positiewissel (coalitie <-> oppositie): inzet per fase, nooit opgeteld.
        resultaat["inzet"] = {
            "oordeel": "Per fase",
            "markeringen": ["positiewissel"] + (["voorlopig"] if open_ else []),
            "fasen": [
                {"positie": f["positie"], "van": f["van"], "tot": f["tot"], **inzet_oordeel(f["items"], open_)}
                for f in fasen
            ],
        }
        return resultaat
    resultaat["inzet"] = inzet_oordeel(items, open_)
    return resultaat


def inzet_oordeel(items: list[dict], open_: list) -> dict:
    """Inzetscore met band, gevoeligheids- en robuustheidscheck voor één reeks stemmingen."""
    inzet = reken_inzet(items)
    if not inzet or inzet["som_gewichten"] < MIN_BEWIJS:
        return {"oordeel": "Onvoldoende bewijs", **(inzet or {})}
    markeringen = []
    gewicht_per_cluster = defaultdict(float)
    for it in items:
        gewicht_per_cluster[it["cluster"]] += it["w"]
    zwaarste = max(sorted(gewicht_per_cluster), key=lambda c: gewicht_per_cluster[c])
    zonder = reken_inzet([dict(it) for it in items if it["cluster"] != zwaarste])
    if not zonder or band(zonder["score"]) != band(inzet["score"]):
        markeringen.append("onzeker")
    strikt = reken_inzet([dict(it) for it in items if it["type"] != "motie"])
    if strikt and band(strikt["score"]) != band(inzet["score"]):
        markeringen.append("selectiegevoelig")
    if open_:
        markeringen.append("voorlopig")
    if any(it.get("coalitiediscipline") for it in items):
        markeringen.append("coalitiediscipline")
    return {
        "oordeel": band(inzet["score"]),
        **inzet,
        "markeringen": markeringen,
        "zonder_zwaarste_cluster": zonder["score"] if zonder else None,
        "alleen_wetten_en_amendementen": strikt["score"] if strikt else None,
    }
    return resultaat


def main() -> int:
    if not BELOFTEN.exists():
        print("Geen map 'beloften' gevonden; niets te verwerken.")
        return 0
    besluiten = lees_besluiten()
    tijdlijn = Tijdlijn(TIJDLIJN)
    if not tijdlijn.beschikbaar:
        print("Geen tijdlijn gevonden: positie (coalitie/oppositie) blijft onbekend.")
    state_pad = DATA / "sync_state.json"
    peildatum = lees_json(state_pad).get("watermerk") if state_pad.exists() else None
    rij, fout_gevonden = [], False
    alle_paren = defaultdict(list)
    betrouwbaarheid = {"streefwaarde_kappa": 0.7, "per_belofte": {}}
    for pad in sorted(BELOFTEN.glob("*.json")):
        if pad.name.startswith("_"):
            continue
        belofte = lees_json(pad)
        ontbreekt = [v for v in ("id", "partij", "zoektermen") if not belofte.get(v)]
        if ontbreekt or belofte.get("id") != pad.stem:
            print(f"FOUT {pad.name}: verplichte velden ontbreken {ontbreekt} of id wijkt af van bestandsnaam")
            fout_gevonden = True
            continue
        if not belofte.get("fracties") and not tijdlijn.alle_fracties(belofte["partij"]):
            print(f"FOUT {pad.name}: partij '{belofte['partij']}' staat niet in tijdlijn/partijen.json en 'fracties' is leeg")
            fout_gevonden = True
            continue
        if len(belofte["zoektermen"]) > 10:
            print(f"FOUT {pad.name}: maximaal tien zoektermen")
            fout_gevonden = True
            continue
        kandidaten = zoek_kandidaten(belofte, besluiten, tijdlijn)
        schrijf_json(
            DATA / "kandidaten" / f"{belofte['id']}.json",
            {
                "belofte_id": belofte["id"],
                "selectie": {
                    "zoektermen": belofte["zoektermen"],
                    "dossiers": belofte.get("dossiers", []),
                    "periode_van": belofte.get("periode_van"),
                    "periode_tot": belofte.get("periode_tot"),
                    "fracties": belofte.get("fracties") or sorted(tijdlijn.alle_fracties(belofte["partij"])),
                    "peildatum": peildatum,
                    "aantal_treffers": len(kandidaten),
                },
                "kandidaten": kandidaten,
            },
        )
        coderingen, beslissingen = lees_coderingen(belofte["id"])
        definitief, stand = bepaal_definitief(kandidaten, coderingen, beslissingen)
        score = bereken_score(belofte, kandidaten, definitief)
        score["codering"] = {"codeurs": sorted(coderingen), **stand}
        score["resultaat"] = lees_resultaat(belofte["id"])
        paren = codeurparen(coderingen)
        for naam, p in paren.items():
            alle_paren[naam].extend(p)
        betrouwbaarheid["per_belofte"][belofte["id"]] = {
            naam: {"n": len(p), "kappa": kappa(p)} for naam, p in paren.items()
        }
        schrijf_json(DATA / "scores" / f"{belofte['id']}.json", score)
        for f in score["fouten"]:
            print(f"LET OP {belofte['id']}: {f}")
        rij.append(
            {
                "belofte_id": belofte["id"],
                "partij": belofte["partij"],
                "positie": score["positie"],
                "kandidaten": len(kandidaten),
                **stand,
                "inzet": score["inzet"].get("oordeel"),
                "resultaat": score["resultaat"]["oordeel"],
                "resultaat_status": score["resultaat"]["status"],
            }
        )
        print(
            f"{belofte['id']}: {len(kandidaten)} kandidaten, {stand['definitief']} definitief, "
            f"{stand['geschil']} geschil, {stand['een_codering'] + stand['ongecodeerd']} te coderen"
        )
    betrouwbaarheid["totaal"] = {
        naam: {"n": len(p), "kappa": kappa(p)} for naam, p in sorted(alle_paren.items())
    }
    schrijf_json(DATA / "betrouwbaarheid.json", betrouwbaarheid)
    schrijf_json(DATA / "beoordelingsrij.json", rij)
    return 1 if fout_gevonden else 0


if __name__ == "__main__":
    sys.exit(main())
