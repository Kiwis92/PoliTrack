"""Tests voor de AI-codeur en de resultaatsuggesties, met een nagebootst model."""
import datetime
import json

import suggesties as g
import verwerk_beloften as v
from conftest import HUURBELOFTE, lees, rekenvoorbeeld, schrijf, schrijf_besluiten


class NepModel:
    """Codeert alles 'voor_belofte', laat één stemming weg, geeft één keer geen richting
    en verzint één sleutel. Onthoudt wat het te zien kreeg."""

    def __init__(self):
        self.berichten = []

    def __call__(self, systeem, bericht, tool, sleutel):
        self.berichten.append(bericht)
        if tool["name"] != "leg_coderingen_vast":
            return {"oordeel": "loopt_nog", "onderbouwing": "o", "te_controleren": ["Eerste Kamer"],
                    "per_kernelement": [{"kernelement": "huur omlaag", "stand": "in gang"}]}
        items = json.loads(bericht.split("STEMMINGEN (JSON)\n")[1].split("\n\nCodeer")[0])
        uit = []
        for it in items:
            assert set(it) == {"sleutel", "type", "datum", "titel", "onderwerp"}, "AI ziet geen stemgedrag"
            if "bevriezing 3" in it["onderwerp"]:
                continue
            if "bevriezing 2" in it["onderwerp"]:
                uit.append({"sleutel": it["sleutel"], "opname": True, "toelichting": "x"})
                continue
            uit.append({"sleutel": it["sleutel"], "opname": True, "richting_voorstem": "voor_belofte",
                        "directheid": 1, "onderzoeksmotie": False, "toelichting": "t"})
        uit.append({"sleutel": "verzonnen", "opname": True, "richting_voorstem": "voor_belofte", "toelichting": "x"})
        return {"coderingen": uit}


def zet_pilot(werkmap):
    schrijf_besluiten(werkmap, rekenvoorbeeld())
    schrijf(werkmap / "beloften" / "vvd-2023-huur.json", HUURBELOFTE)
    assert v.main() == 0
    return lees(werkmap / "data" / "kandidaten" / "vvd-2023-huur.json")["kandidaten"]


def test_ai_codeur_is_blind_en_robuust(werkmap):
    kand = zet_pilot(werkmap)
    model = NepModel()
    assert g.codeer(HUURBELOFTE, kand, "sleutel", 300, vraag=model) == 6
    ai = lees(werkmap / "beoordelingen" / "vvd-2023-huur" / "codering-ai.json")
    assert len(ai["coderingen"]) == 6 and "verzonnen" not in ai["coderingen"]
    assert sum(1 for c in ai["coderingen"].values() if c["opname"] is False and c["reden_code"] == "U3") == 1
    assert "partijstem" not in model.berichten[0] and '"Voor"' not in model.berichten[0]
    # Alleen de vergeten stemming wordt opnieuw aangeboden.
    assert g.codeer(HUURBELOFTE, kand, "sleutel", 300, vraag=lambda *a: {"coderingen": []}) == 0
    assert g.codeer(HUURBELOFTE, kand, "sleutel", 0, vraag=model) == 0, "budget 0 doet niets"


def test_resultaatsuggestie_regels_en_ai(werkmap):
    kand = zet_pilot(werkmap)
    for codeur in ("ai", "billy"):
        schrijf(werkmap / "beoordelingen" / "vvd-2023-huur" / f"codering-{codeur}.json", {
            "codeur": codeur,
            "coderingen": {k["sleutel"]: {"opname": True, "richting_voorstem": "voor_belofte", "directheid": 1} for k in kand}})
    v.main()
    score = lees(werkmap / "data" / "scores" / "vvd-2023-huur.json")
    model = NepModel()
    assert g.resultaat_suggestie(HUURBELOFTE, score, "sleutel", vraag=model) is True
    sg = lees(werkmap / "data" / "resultaat_suggesties" / "vvd-2023-huur.json")
    assert sg["regel"]["oordeel"] == "loopt_nog"
    assert sg["regel"]["feiten"]["wetten_voor_belofte_aangenomen_tk"] == ["2026Za1"]
    assert sg["ai"]["te_controleren"] == ["Eerste Kamer"]
    assert g.resultaat_suggestie(HUURBELOFTE, score, "sleutel", vraag=model) is False, "zelfde invoer: geen nieuwe aanroep"
    assert g.resultaat_suggestie(HUURBELOFTE, score, None, vraag=model) is False, "zonder sleutel geen AI"


def test_regel_horizon_verstreken():
    r = g.regel_suggestie(HUURBELOFTE | {"horizon": "2025-01-01"}, {"opgenomen": []}, datetime.date(2026, 11, 15))
    assert r["oordeel"] == "niet_gerealiseerd"
    r = g.regel_suggestie(HUURBELOFTE, {"opgenomen": []}, datetime.date(2026, 11, 15))
    assert r["oordeel"] == "loopt_nog"


def test_regel_wet_tegen_belofte():
    wet = {"type": "wet", "richting_voorstem": "tegen_belofte", "besluit": "Aangenomen.", "zaaknummer": "X"}
    r = g.regel_suggestie(HUURBELOFTE, {"opgenomen": [wet]}, datetime.date(2026, 11, 15))
    assert r["oordeel"] == "loopt_nog" and "Eerste Kamer" in r["uitleg"]
    assert r["feiten"]["wetten_tegen_belofte_aangenomen_tk"] == ["X"]


def test_schoon_codering_vult_gaten():
    assert g.schoon_codering({"opname": True})["reden_code"] == "U3"
    c = g.schoon_codering({"opname": True, "richting_voorstem": "tegen_belofte", "directheid": 0.5})
    assert c["opname"] is True and c["directheid"] == 0.5
    assert g.schoon_codering({"opname": False, "reden_code": "U9"})["reden_code"] == "U3"
