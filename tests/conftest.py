"""Gedeelde hulpjes voor de tests.

Alle tests draaien in een tijdelijke map: ze raken de echte mappen
beloften/, beoordelingen/, resultaten/ en data/ nooit aan.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import suggesties  # noqa: E402
import sync_stemmingen  # noqa: E402
import verwerk_beloften  # noqa: E402


@pytest.fixture
def werkmap(tmp_path, monkeypatch):
    """Wijst alle pipeline-modules naar een lege tijdelijke map."""
    for mod in (verwerk_beloften, suggesties):
        monkeypatch.setattr(mod, "BELOFTEN", tmp_path / "beloften")
        monkeypatch.setattr(mod, "BEOORDELINGEN", tmp_path / "beoordelingen")
        monkeypatch.setattr(mod, "DATA", tmp_path / "data")
    monkeypatch.setattr(verwerk_beloften, "RESULTATEN", tmp_path / "resultaten")
    monkeypatch.setattr(verwerk_beloften, "TIJDLIJN", tmp_path / "tijdlijn", raising=False)
    monkeypatch.setattr(sync_stemmingen, "DATA", tmp_path / "data")
    monkeypatch.setattr(sync_stemmingen, "STATE", tmp_path / "data" / "sync_state.json")
    return tmp_path


def schrijf(pad: Path, inhoud) -> None:
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(json.dumps(inhoud, ensure_ascii=False, indent=1), encoding="utf-8")


def lees(pad: Path):
    return json.loads(pad.read_text(encoding="utf-8"))


def besluit(
    i: str,
    dag: str,
    soort: str,
    onderwerp: str,
    stem_vvd: str,
    dossier: str = "36000",
    besluittekst: str = "Aangenomen.",
    stemmingen: list | None = None,
) -> dict:
    """Een opgeslagen besluit zoals sync_stemmingen het wegschrijft."""
    if stemmingen is None:
        stemmingen = [
            {"id": "s" + i, "fractie": "VVD", "fractie_id": "f-vvd", "actor": "VVD", "persoon_id": None,
             "stem": stem_vvd, "fractiegrootte": 22, "vergissing": False},
            {"id": "t" + i, "fractie": "SP", "fractie_id": "f-sp", "actor": "SP", "persoon_id": None,
             "stem": "Voor", "fractiegrootte": 3, "vergissing": False},
        ]
    return {
        "besluit_id": i + "0" * (32 - len(i)),
        "datum": dag + "T15:00:00+01:00",
        "stemmingssoort": "Met handopsteken",
        "besluitsoort": "Stemmen - " + besluittekst.lower().rstrip("."),
        "besluittekst": besluittekst,
        "status": "Besluit",
        "zaken": [{"id": "z" + i, "nummer": "2026Z" + i, "soort": soort, "titel": "Huurwet",
                   "onderwerp": onderwerp, "gestart_op": dag, "volgnummer": 1, "dossiers": [dossier]}],
        "stemmingen": stemmingen,
    }


def schrijf_besluiten(werkmap: Path, besluiten: list[dict]) -> None:
    for b in besluiten:
        schrijf(werkmap / "data" / "besluiten" / b["besluit_id"][:2] / (b["besluit_id"] + ".json"), b)


HUURBELOFTE = {
    "id": "vvd-2023-huur",
    "partij": "VVD",
    "fracties": ["VVD"],
    "verkiezingsjaar": 2023,
    "zoektermen": ["huur"],
    "dossiers": [],
    "periode_van": "2023-12-06",
    "periode_tot": None,
    "citaat": "Wij verlagen de huur",
    "doel": "Huur omlaag",
    "richting": "Stem voor lagere huur",
    "kernelementen": ["huur omlaag"],
    "horizon": "2027-12-31",
}


def rekenvoorbeeld() -> list[dict]:
    """Het rekenvoorbeeld uit de methode: wet voor (5), amendement tegen (3),
    vier moties tegen in één debat (samen 1), losse motie voor (1) -> 6/10."""
    return [
        besluit("a1", "2026-03-10", "Wetgeving", "Wet betaalbare huur", "Voor"),
        besluit("a2", "2026-03-10", "Amendement", "Amendement huurprijs", "Tegen", besluittekst="Verworpen."),
        *[besluit(f"b{n}", "2026-02-03", "Motie", f"Motie huurbevriezing {n}", "Tegen", besluittekst="Verworpen.") for n in range(4)],
        besluit("c1", "2026-05-12", "Motie", "Motie over huur verlagen", "Voor", dossier="32847"),
    ]
