"""Tijdlijn van partijen, fracties en coalities.

Leest tijdlijn/partijen.json en tijdlijn/kabinetten.json en beantwoordt drie
vragen voor een partij op een dag:

- welke fractienamen in de Kamerdata horen bij deze partij? (fracties_op)
- zat de partij in de coalitie of de oppositie? (positie_op)
- waar lopen de fasen (coalitie/oppositie) in een reeks stemmingen? (fasen)

Zonder tijdlijnbestanden werkt de verwerking gewoon door: dan geldt het veld
"fracties" uit de belofte en is de positie onbekend.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIJDLIJN = ROOT / "tijdlijn"


def _lees(pad: Path) -> dict:
    return json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}


class Tijdlijn:
    def __init__(self, map_: Path | None = None):
        map_ = map_ or TIJDLIJN
        self.partijen = _lees(map_ / "partijen.json").get("partijen", {})
        self.kabinetten = _lees(map_ / "kabinetten.json").get("kabinetten", [])

    @property
    def beschikbaar(self) -> bool:
        return bool(self.partijen) or bool(self.kabinetten)

    @staticmethod
    def _geldig(item: dict, dag: str) -> bool:
        van, tot = item.get("van"), item.get("tot")
        return (not van or van <= dag) and (not tot or dag <= tot)

    def fracties_op(self, partij: str, dag: str) -> set[str]:
        """Fractienamen (kleine letters) die op deze dag bij de partij horen."""
        info = self.partijen.get(partij)
        if not info:
            return set()
        return {f["fractie"].lower() for f in info["fracties"] if self._geldig(f, dag)}

    def alle_fracties(self, partij: str) -> set[str]:
        info = self.partijen.get(partij)
        return {f["fractie"].lower() for f in info["fracties"]} if info else set()

    def positie_op(self, partij: str, dag: str) -> dict:
        """{"positie": "coalitie"|"oppositie"|"onbekend", "kabinet": ..., "demissionair": bool}"""
        if not self.kabinetten:
            return {"positie": "onbekend", "kabinet": None, "demissionair": False}
        for kab in self.kabinetten:
            if not self._geldig(kab, dag):
                continue
            demissionair = bool(kab.get("demissionair_vanaf")) and kab["demissionair_vanaf"] <= dag
            for lid in kab.get("coalitie", []):
                if lid["partij"] == partij and self._geldig(lid, dag):
                    return {"positie": "coalitie", "kabinet": kab["naam"], "demissionair": demissionair}
            for lid in kab.get("gedoog", []):
                if lid["partij"] == partij and self._geldig(lid, dag):
                    return {"positie": "gedoog", "kabinet": kab["naam"], "demissionair": demissionair}
            return {"positie": "oppositie", "kabinet": kab["naam"], "demissionair": demissionair}
        return {"positie": "onbekend", "kabinet": None, "demissionair": False}

    @staticmethod
    def fasen(items: list[dict]) -> list[dict]:
        """Deelt chronologisch gesorteerde items (met 'datum' en 'positie') op in
        aaneengesloten fasen met dezelfde positie."""
        uit: list[dict] = []
        for it in sorted(items, key=lambda x: x["datum"]):
            if uit and uit[-1]["positie"] == it["positie"]:
                uit[-1]["tot"] = it["datum"]
                uit[-1]["items"].append(it)
            else:
                uit.append({"positie": it["positie"], "van": it["datum"], "tot": it["datum"], "items": [it]})
        return uit
