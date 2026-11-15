#!/usr/bin/env python3
"""Koppelt opgehaalde stemmingen aan beloften en rekent de inzetscore uit.

Invoer
------
beloften/<id>.json        Vooraf vastgelegde belofte: zoektermen, dossiers, periode.
                          Bestanden die met een underscore beginnen worden overgeslagen.
beoordelingen/<id>.json   Menselijke beslissingen per stemming (opname, richting, ...).
data/besluiten/           Opgehaalde stemmingen (zie sync_stemmingen.py).

Uitvoer (wordt elke run opnieuw gemaakt, niet met de hand aanpassen)
------
data/kandidaten/<id>.json   Het zoekuniversum: alle stemmingen die mechanisch matchen.
data/scores/<id>.json       Inzetscore volgens methode v2, voor zover beoordeeld.
data/beoordelingsrij.json   Overzicht: hoeveel kandidaten per belofte nog wachten.

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

ROOT = Path(__file__).resolve().parent.parent
BELOFTEN = ROOT / "beloften"
BEOORDELINGEN = ROOT / "beoordelingen"
DATA = ROOT / "data"

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


def zoek_kandidaten(belofte: dict, besluiten: list[dict]) -> list[dict]:
    termen = [t.lower() for t in belofte.get("zoektermen", [])]
    dossiers = {str(d) for d in belofte.get("dossiers", [])}
    van, tot = belofte.get("periode_van") or "", belofte.get("periode_tot") or "9999"
    fracties = {f.lower() for f in belofte["fracties"]}
    kandidaten = []
    for b in besluiten:
        dag = (b.get("datum") or "")[:10]
        if not dag or not (van <= dag <= tot):
            continue
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


def bereken_score(belofte: dict, kandidaten: list[dict], beoordeling: dict) -> dict:
    per_sleutel = {k["sleutel"]: k for k in kandidaten}
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
                "cluster": k["cluster"],
                "c": round(consistent / deelgenomen, 4),
                "d": d,
                "onderzoeksmotie": bool(oordeel.get("onderzoeksmotie")),
                "coalitiediscipline": bool(oordeel.get("coalitiediscipline")),
            }
        )
    for sleutel in beoordeling:
        if sleutel not in per_sleutel:
            fouten.append(f"{sleutel}: beoordeeld maar geen kandidaat (meer)")

    resultaat = {
        "belofte_id": belofte["id"],
        "methode": "v2",
        "opgenomen": items,
        "uitgesloten": uitgesloten,
        "nog_te_beoordelen": len(open_),
        "fouten": fouten,
    }
    inzet = reken_inzet(items)
    if not inzet or inzet["som_gewichten"] < MIN_BEWIJS:
        resultaat["inzet"] = {"oordeel": "Onvoldoende bewijs", **(inzet or {})}
        return resultaat

    markeringen = []
    # Gevoeligheid: haal het zwaarste cluster weg.
    gewicht_per_cluster = defaultdict(float)
    for it in items:
        gewicht_per_cluster[it["cluster"]] += it["w"]
    zwaarste = max(sorted(gewicht_per_cluster), key=lambda c: gewicht_per_cluster[c])
    zonder = reken_inzet([dict(it) for it in items if it["cluster"] != zwaarste])
    if not zonder or band(zonder["score"]) != band(inzet["score"]):
        markeringen.append("onzeker")
    # Robuustheid: alleen wetten en amendementen.
    strikt = reken_inzet([dict(it) for it in items if it["type"] != "motie"])
    if strikt and band(strikt["score"]) != band(inzet["score"]):
        markeringen.append("selectiegevoelig")
    if open_:
        markeringen.append("voorlopig")

    resultaat["inzet"] = {
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
    state_pad = DATA / "sync_state.json"
    peildatum = lees_json(state_pad).get("watermerk") if state_pad.exists() else None
    rij, fout_gevonden = [], False
    for pad in sorted(BELOFTEN.glob("*.json")):
        if pad.name.startswith("_"):
            continue
        belofte = lees_json(pad)
        ontbreekt = [v for v in ("id", "partij", "fracties", "zoektermen") if not belofte.get(v)]
        if ontbreekt or belofte.get("id") != pad.stem:
            print(f"FOUT {pad.name}: verplichte velden ontbreken {ontbreekt} of id wijkt af van bestandsnaam")
            fout_gevonden = True
            continue
        if len(belofte["zoektermen"]) > 10:
            print(f"FOUT {pad.name}: maximaal tien zoektermen")
            fout_gevonden = True
            continue
        kandidaten = zoek_kandidaten(belofte, besluiten)
        schrijf_json(
            DATA / "kandidaten" / f"{belofte['id']}.json",
            {
                "belofte_id": belofte["id"],
                "selectie": {
                    "zoektermen": belofte["zoektermen"],
                    "dossiers": belofte.get("dossiers", []),
                    "periode_van": belofte.get("periode_van"),
                    "periode_tot": belofte.get("periode_tot"),
                    "fracties": belofte["fracties"],
                    "peildatum": peildatum,
                    "aantal_treffers": len(kandidaten),
                },
                "kandidaten": kandidaten,
            },
        )
        beoordeling_pad = BEOORDELINGEN / f"{belofte['id']}.json"
        beoordeling = lees_json(beoordeling_pad) if beoordeling_pad.exists() else {}
        score = bereken_score(belofte, kandidaten, beoordeling)
        schrijf_json(DATA / "scores" / f"{belofte['id']}.json", score)
        for f in score["fouten"]:
            print(f"LET OP {belofte['id']}: {f}")
        rij.append(
            {
                "belofte_id": belofte["id"],
                "partij": belofte["partij"],
                "kandidaten": len(kandidaten),
                "nog_te_beoordelen": score["nog_te_beoordelen"],
                "inzet": score["inzet"].get("oordeel"),
            }
        )
        print(f"{belofte['id']}: {len(kandidaten)} kandidaten, {score['nog_te_beoordelen']} te beoordelen")
    schrijf_json(DATA / "beoordelingsrij.json", rij)
    return 1 if fout_gevonden else 0


if __name__ == "__main__":
    sys.exit(main())
