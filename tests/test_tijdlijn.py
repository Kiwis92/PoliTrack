"""Tests voor de tijdlijn van partijen, fracties en coalities."""
from pathlib import Path

import pytest

import tijdlijn_check
import verwerk_beloften as v
from conftest import HUURBELOFTE, besluit, lees, schrijf, schrijf_besluiten
from tijdlijn import Tijdlijn

ECHTE = Tijdlijn(Path(__file__).resolve().parent.parent / "tijdlijn")


@pytest.mark.parametrize("partij, dag, positie, kabinet", [
    ("PVV", "2024-07-02", "coalitie", "Schoof"),
    ("PVV", "2025-06-03", "oppositie", "Schoof"),
    ("NSC", "2025-08-21", "coalitie", "Schoof"),
    ("NSC", "2025-08-22", "oppositie", "Schoof"),
    ("VVD", "2026-02-22", "coalitie", "Schoof"),
    ("VVD", "2026-02-23", "coalitie", "Jetten"),
    ("D66", "2026-02-22", "oppositie", "Schoof"),
    ("D66", "2026-02-23", "coalitie", "Jetten"),
    ("GL-PvdA", "2026-06-15", "oppositie", "Jetten"),
    ("CDA", "2024-01-15", "coalitie", "Rutte IV (demissionair)"),
    ("PVV", "2010-01-01", "onbekend", None),
])
def test_positie_in_echte_tijdlijn(partij, dag, positie, kabinet):
    p = ECHTE.positie_op(partij, dag)
    assert (p["positie"], p["kabinet"]) == (positie, kabinet)


def test_demissionair_vlag():
    assert ECHTE.positie_op("VVD", "2025-06-02")["demissionair"] is False
    assert ECHTE.positie_op("VVD", "2025-06-03")["demissionair"] is True


def test_fusie_erft_en_afsplitsing_niet():
    assert ECHTE.fracties_op("GL-PvdA", "2026-06-08") == {"groenlinks-pvda"}
    assert ECHTE.fracties_op("GL-PvdA", "2026-06-09") == {"groenlinks-pvda", "pro"}, "overgangsdag volgens de API"
    assert ECHTE.fracties_op("GL-PvdA", "2026-06-11") == {"pro"}
    assert ECHTE.fracties_op("PVV", "2026-03-01") == {"pvv"}, "Groep Markuszower telt niet voor de PVV"
    assert ECHTE.partijen["Groep Markuszower"]["afgesplitst_van"] == "PVV"
    assert ECHTE.fracties_op("Onbekend", "2026-01-01") == set()


def test_fasen_splitst_op_positiewissel():
    items = [{"datum": "2025-01-01", "positie": "coalitie"}, {"datum": "2025-03-01", "positie": "coalitie"},
             {"datum": "2025-07-01", "positie": "oppositie"}, {"datum": "2024-12-01", "positie": "coalitie"}]
    f = Tijdlijn.fasen(items)
    assert [(x["positie"], x["van"], x["tot"], len(x["items"])) for x in f] == [
        ("coalitie", "2024-12-01", "2025-03-01", 3), ("oppositie", "2025-07-01", "2025-07-01", 1)]


def test_positiewissel_geeft_inzet_per_fase(werkmap, monkeypatch):
    monkeypatch.setattr(v, "TIJDLIJN", Path(__file__).resolve().parent.parent / "tijdlijn")
    pvv = lambda i, dag, stem: besluit(i, dag, "Motie", f"Motie asiel {i}", "Voor", stemmingen=[
        {"id": "s" + i, "fractie": "PVV", "fractie_id": "f", "actor": "PVV", "persoon_id": None, "stem": stem, "fractiegrootte": 37, "vergissing": False}])
    # Coalitie: 1 van 3 consistent. Oppositie: 3 van 3 consistent. Opgeteld zou 4/6 'overwegend consistent' zijn.
    schrijf_besluiten(werkmap, [pvv("a", "2024-09-10", "Tegen"), pvv("b", "2024-10-08", "Tegen"), pvv("c", "2024-11-12", "Voor"),
                                pvv("d", "2025-07-01", "Voor"), pvv("e", "2025-09-02", "Voor"), pvv("f", "2025-10-07", "Voor")])
    schrijf(werkmap / "beloften" / "pvv-2023-asiel.json", HUURBELOFTE | {"id": "pvv-2023-asiel", "partij": "PVV", "fracties": [], "zoektermen": ["asiel"]})
    assert v.main() == 0
    kand = lees(werkmap / "data" / "kandidaten" / "pvv-2023-asiel.json")["kandidaten"]
    assert [k["positie"] for k in kand] == ["coalitie"] * 3 + ["oppositie"] * 3
    assert kand[0]["fracties"] == ["pvv"] and kand[0]["kabinet"] == "Schoof"
    for codeur in ("ai", "billy"):
        schrijf(werkmap / "beoordelingen" / "pvv-2023-asiel" / f"codering-{codeur}.json", {"codeur": codeur, "coderingen": {
            k["sleutel"]: {"opname": True, "richting_voorstem": "voor_belofte", "directheid": 1} for k in kand}})
    v.main()
    s = lees(werkmap / "data" / "scores" / "pvv-2023-asiel.json")
    assert s["positie"] == "wisselend"
    assert s["inzet"]["oordeel"] == "Per fase" and "positiewissel" in s["inzet"]["markeringen"]
    assert [(f["positie"], f["oordeel"]) for f in s["inzet"]["fasen"]] == [("coalitie", "Strijdig"), ("oppositie", "Consistent")]
    assert "score" not in s["inzet"], "fasen worden nooit opgeteld"


def test_zonder_tijdlijn_blijft_positie_onbekend(werkmap):
    schrijf_besluiten(werkmap, [besluit("a1", "2026-03-10", "Motie", "Motie huur", "Voor")])
    schrijf(werkmap / "beloften" / "vvd-2023-huur.json", HUURBELOFTE)
    assert v.main() == 0
    k = lees(werkmap / "data" / "kandidaten" / "vvd-2023-huur.json")["kandidaten"]
    assert k[0]["positie"] == "onbekend"


def test_onbekende_partij_zonder_fracties_is_fout(werkmap, monkeypatch):
    monkeypatch.setattr(v, "TIJDLIJN", Path(__file__).resolve().parent.parent / "tijdlijn")
    schrijf(werkmap / "beloften" / "x.json", HUURBELOFTE | {"id": "x", "partij": "Bestaat niet", "fracties": []})
    assert v.main() == 1


def test_tijdlijn_check_waarschuwt_voor_onbekende_fractie():
    fracties = [{"fractie": "PVV", "zetels": 19, "van": "2006-11-30", "tot": None},
                {"fractie": "Nieuw Sociaal Contract", "zetels": 19, "van": "2023-12-05", "tot": "2025-11-11"},
                {"fractie": "Groep Nieuw", "zetels": 2, "van": "2026-09-01", "tot": None},
                {"fractie": "PRO", "zetels": 20, "van": "2026-06-11", "tot": None}]
    w = tijdlijn_check.controleer(fracties, ECHTE)
    assert len(w) == 2, w
    assert "Groep Nieuw" in w[0]
    assert "PRO" in w[1] and "2026-06-09" in w[1] and "2026-06-11" in w[1]


def test_tijdlijn_klopt_met_api_stand_van_15_november_2026():
    """Fracties zoals de API ze op 15 november 2026 gaf."""
    api = [("SGP", "1922-04-30", None), ("VVD", "1948-01-23", None), ("D66", "1966-10-13", None), ("CDA", "1980-10-11", None),
           ("SP", "1994-05-17", None), ("ChristenUnie", "2001-03-15", None), ("PVV", "2006-11-30", None), ("PvdD", "2006-11-30", None),
           ("FVD", "2017-03-23", None), ("DENK", "2017-03-23", None), ("BBB", "2021-03-31", None), ("JA21", "2021-03-31", None),
           ("Volt", "2021-03-31", None), ("GroenLinks-PvdA", "2023-10-27", "2026-06-10"), ("Nieuw Sociaal Contract", "2023-12-05", "2025-11-11"),
           ("50PLUS", "2025-11-12", None), ("Groep Markuszower", "2026-01-20", None), ("Lid Keijzer", "2026-02-24", None), ("PRO", "2026-06-09", None)]
    fracties = [{"fractie": f, "zetels": 1, "van": van, "tot": tot} for f, van, tot in api]
    assert tijdlijn_check.controleer(fracties, ECHTE) == []
