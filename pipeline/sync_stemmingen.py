#!/usr/bin/env python3
"""Haalt nieuwe en gewijzigde stemmingen op uit de Tweede Kamer OData API.

Werking
-------
1. Vraag alle Stemming-records op die gewijzigd zijn sinds de vorige run
   (veld ApiGewijzigdOp), oplopend gesorteerd.
2. Haal voor elk geraakt Besluit het volledige besluit opnieuw op, met alle
   stemmingen, de gekoppelde zaken (motie, amendement, wet) en de datum.
3. Schrijf elk besluit naar data/besluiten/<xx>/<besluit-id>.json.
4. Bewaar per pagina hoe ver we zijn in data/sync_state.json, zodat een
   afgebroken run de volgende keer verdergaat waar hij bleef.

Het script gebruikt alleen de Python-standaardbibliotheek.

Gebruik
-------
    python pipeline/sync_stemmingen.py                 # normale run
    python pipeline/sync_stemmingen.py --vanaf 2023-12-06T00:00:00Z
    python pipeline/sync_stemmingen.py --max-paginas 5 # korte testrun
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/"
# Begin van de zittingsperiode na de verkiezingen van november 2023.
STANDAARD_VANAF = "2023-12-06T00:00:00Z"
BATCH = 15  # aantal besluiten per verzoek (houdt de URL kort)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATE = DATA / "sync_state.json"

BESLUIT_QUERY = (
    "$select=Id,StemmingsSoort,BesluitSoort,BesluitTekst,Status,GewijzigdOp,Verwijderd"
    "&$expand=Zaak($select=Id,Nummer,Soort,Volgnummer,Titel,Onderwerp,GestartOp;"
    "$expand=Kamerstukdossier($select=Nummer,Toevoeging)),"
    "Stemming($select=Id,Soort,ActorNaam,ActorFractie,FractieGrootte,Vergissing,"
    "Persoon_Id,Fractie_Id,Verwijderd),"
    "Agendapunt($select=Id;$expand=Activiteit($select=Id,Datum,Soort))"
)


def haal_op(url: str, pogingen: int = 5) -> dict:
    """GET met herhaalpogingen; geeft de JSON-inhoud terug."""
    laatste_fout: Exception | None = None
    for poging in range(pogingen):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "BeloofdEnGedaan-sync/1.0 (github.com/Kiwis92/PoliTrack)",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as fout:
            laatste_fout = fout
            time.sleep(2 ** poging)
    raise RuntimeError(f"API niet bereikbaar na {pogingen} pogingen: {url}") from laatste_fout


def url_voor(entiteit: str, query: str) -> str:
    return API + entiteit + "?" + urllib.parse.quote(query, safe="=&$(),;'")


def lees_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def schrijf_state(state: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pad_voor(besluit_id: str) -> Path:
    return DATA / "besluiten" / besluit_id[:2] / f"{besluit_id}.json"


def vorm_besluit(ruw: dict) -> dict:
    """Zet een API-besluit om naar het compacte opslagformaat."""
    activiteit = ((ruw.get("Agendapunt") or {}).get("Activiteit")) or {}
    stemmingen = [
        {
            "id": s["Id"],
            "fractie": s.get("ActorFractie"),
            "fractie_id": s.get("Fractie_Id"),
            "actor": s.get("ActorNaam"),
            "persoon_id": s.get("Persoon_Id"),
            "stem": s.get("Soort"),
            "fractiegrootte": s.get("FractieGrootte"),
            "vergissing": s.get("Vergissing"),
        }
        for s in ruw.get("Stemming", [])
        if not s.get("Verwijderd")
    ]
    stemmingen.sort(key=lambda s: ((s["fractie"] or ""), (s["actor"] or ""), s["id"]))
    zaken = [
        {
            "id": z["Id"],
            "nummer": z.get("Nummer"),
            "soort": z.get("Soort"),
            "titel": z.get("Titel"),
            "onderwerp": z.get("Onderwerp"),
            "gestart_op": z.get("GestartOp"),
            "volgnummer": z.get("Volgnummer"),
            "dossiers": sorted(
                str(d.get("Nummer")) + (f"-{d['Toevoeging']}" if d.get("Toevoeging") else "")
                for d in z.get("Kamerstukdossier", [])
                if d.get("Nummer") is not None
            ),
        }
        for z in ruw.get("Zaak", [])
    ]
    zaken.sort(key=lambda z: z["id"])
    return {
        "besluit_id": ruw["Id"],
        "datum": activiteit.get("Datum"),
        "stemmingssoort": ruw.get("StemmingsSoort"),
        "besluitsoort": ruw.get("BesluitSoort"),
        "besluittekst": ruw.get("BesluitTekst"),
        "status": ruw.get("Status"),
        "zaken": zaken,
        "stemmingen": stemmingen,
    }


def verwerk_besluiten(besluit_ids: list[str], haal=haal_op) -> tuple[int, int]:
    """Haalt besluiten op en schrijft ze weg. Geeft (geschreven, verwijderd) terug."""
    geschreven = verwijderd = 0
    for i in range(0, len(besluit_ids), BATCH):
        groep = besluit_ids[i : i + BATCH]
        filt = " or ".join(f"Id eq {b}" for b in groep)
        url = url_voor("Besluit", f"$filter={filt}&{BESLUIT_QUERY}")
        gevonden = set()
        while url:
            antwoord = haal(url)
            for ruw in antwoord.get("value", []):
                gevonden.add(ruw["Id"])
                pad = pad_voor(ruw["Id"])
                besluit = vorm_besluit(ruw)
                if ruw.get("Verwijderd") or not besluit["stemmingen"]:
                    if pad.exists():
                        pad.unlink()
                        verwijderd += 1
                    continue
                pad.parent.mkdir(parents=True, exist_ok=True)
                pad.write_text(
                    json.dumps(besluit, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
                )
                geschreven += 1
            url = antwoord.get("@odata.nextLink")
        # Besluiten die de API niet meer kent, halen we ook lokaal weg.
        for ontbreekt in set(groep) - gevonden:
            pad = pad_voor(ontbreekt)
            if pad.exists():
                pad.unlink()
                verwijderd += 1
    return geschreven, verwijderd


def sync(vanaf: str | None = None, max_paginas: int | None = None, haal=haal_op) -> dict:
    state = lees_state()
    watermerk = vanaf or state.get("watermerk") or STANDAARD_VANAF
    url = url_voor(
        "Stemming",
        f"$select=Besluit_Id,ApiGewijzigdOp&$orderby=ApiGewijzigdOp asc"
        f"&$filter=ApiGewijzigdOp ge {watermerk}",
    )
    totaal_geschreven = totaal_verwijderd = paginas = 0
    while url:
        antwoord = haal(url)
        rijen = antwoord.get("value", [])
        if not rijen:
            break
        ids = sorted({r["Besluit_Id"] for r in rijen if r.get("Besluit_Id")})
        g, v = verwerk_besluiten(ids, haal)
        totaal_geschreven += g
        totaal_verwijderd += v
        watermerk = rijen[-1]["ApiGewijzigdOp"]
        state.update({"watermerk": watermerk})
        schrijf_state(state)
        paginas += 1
        print(f"pagina {paginas}: {len(ids)} besluiten, bijgewerkt t/m {watermerk}", flush=True)
        url = antwoord.get("@odata.nextLink")
        if max_paginas and paginas >= max_paginas:
            break
    state.update(
        {
            "watermerk": watermerk,
            "laatste_run": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "laatste_run_geschreven": totaal_geschreven,
            "laatste_run_verwijderd": totaal_verwijderd,
        }
    )
    schrijf_state(state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--vanaf", help="Begin opnieuw vanaf dit tijdstip (ISO, UTC)")
    parser.add_argument("--max-paginas", type=int, help="Stop na N pagina's (voor testen)")
    args = parser.parse_args()
    state = sync(args.vanaf, args.max_paginas)
    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
