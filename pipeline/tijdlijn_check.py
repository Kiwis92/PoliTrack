#!/usr/bin/env python3
"""Controleert tijdlijn/partijen.json tegen de fracties in de Tweede Kamer-API.

Haalt alle fracties op die sinds 6 december 2023 actief waren, schrijft ze naar
data/tijdlijn/fracties.json en waarschuwt als:
- de API een fractie kent die in tijdlijn/partijen.json ontbreekt;
- de begin- of einddatum in de tijdlijn afwijkt van de API.

Geeft exitcode 0, ook bij waarschuwingen: een nieuwe afsplitsing mag het
ophalen van stemmingen niet tegenhouden. De waarschuwing staat in het logboek
van de run en in data/tijdlijn/fracties.json onder "waarschuwingen".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sync_stemmingen import haal_op, url_voor
from tijdlijn import Tijdlijn

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VANAF = "2023-12-06"


def haal_fracties(haal=haal_op) -> list[dict]:
    url = url_voor(
        "Fractie",
        f"$filter=DatumInactief eq null or DatumInactief ge {VANAF}T00:00:00Z"
        "&$select=Id,Afkorting,NaamNL,AantalZetels,DatumActief,DatumInactief&$orderby=DatumActief",
    )
    uit = []
    while url:
        antwoord = haal(url)
        for f in antwoord.get("value", []):
            if not f.get("Afkorting"):
                continue  # lege historische records
            uit.append(
                {
                    "id": f["Id"],
                    "fractie": f["Afkorting"],
                    "naam": f.get("NaamNL"),
                    "zetels": f.get("AantalZetels"),
                    "van": (f.get("DatumActief") or "")[:10] or None,
                    "tot": (f.get("DatumInactief") or "")[:10] or None,
                }
            )
        url = antwoord.get("@odata.nextLink")
    return uit


def controleer(fracties: list[dict], tijdlijn: Tijdlijn) -> list[str]:
    bekend = {}
    for partij, info in tijdlijn.partijen.items():
        for f in info["fracties"]:
            bekend[f["fractie"].lower()] = (partij, f)
    waarschuwingen = []
    for f in fracties:
        naam = f["fractie"].lower()
        if naam not in bekend:
            waarschuwingen.append(
                f"Fractie '{f['fractie']}' ({f['zetels']} zetels, sinds {f['van']}) staat niet in tijdlijn/partijen.json. "
                "Voeg toe: nieuwe partij, fusie (erft) of afsplitsing (erft niet)."
            )
            continue
        partij, regel = bekend[naam]
        if regel.get("van") and f["van"] and regel["van"] != f["van"] and f["van"] > VANAF:
            waarschuwingen.append(f"'{f['fractie']}': begindatum tijdlijn {regel['van']} wijkt af van API {f['van']}.")
        if f["tot"] and not regel.get("tot"):
            waarschuwingen.append(f"'{f['fractie']}' is volgens de API inactief sinds {f['tot']}; zet 'tot' in tijdlijn/partijen.json.")
    return waarschuwingen


def main() -> int:
    tijdlijn = Tijdlijn()
    fracties = haal_fracties()
    waarschuwingen = controleer(fracties, tijdlijn)
    DATA.joinpath("tijdlijn").mkdir(parents=True, exist_ok=True)
    (DATA / "tijdlijn" / "fracties.json").write_text(
        json.dumps({"bron": "Tweede Kamer OData API, entiteit Fractie", "fracties": fracties, "waarschuwingen": waarschuwingen},
                   indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for w in waarschuwingen:
        print("LET OP tijdlijn:", w)
    print(f"{len(fracties)} fracties gecontroleerd, {len(waarschuwingen)} waarschuwingen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
