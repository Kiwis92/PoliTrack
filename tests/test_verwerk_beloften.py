"""Tests voor selectie, dubbele codering, kappa en de inzetscore."""
import pytest

import verwerk_beloften as v
from conftest import HUURBELOFTE, besluit, lees, rekenvoorbeeld, schrijf, schrijf_besluiten


def zet_pilot(werkmap, extra=()):
    schrijf_besluiten(werkmap, rekenvoorbeeld() + list(extra))
    schrijf(werkmap / "data" / "sync_state.json", {"watermerk": "2026-06-03T00:00:00Z"})
    schrijf(werkmap / "beloften" / "vvd-2023-huur.json", HUURBELOFTE)
    schrijf(werkmap / "beloften" / "_voorbeeld.json", {"x": 1})


def score(werkmap):
    return lees(werkmap / "data" / "scores" / "vvd-2023-huur.json")


def kandidaten(werkmap):
    return lees(werkmap / "data" / "kandidaten" / "vvd-2023-huur.json")


def codeer_alles(werkmap, codeur, kand, richting="voor_belofte", behalve=()):
    schrijf(werkmap / "beoordelingen" / "vvd-2023-huur" / f"codering-{codeur}.json", {
        "codeur": codeur,
        "coderingen": {k["sleutel"]: {"opname": True, "richting_voorstem": richting, "directheid": 1}
                       for k in kand if k["sleutel"] not in behalve},
    })


def test_selectie_is_mechanisch(werkmap):
    hoofdelijk = [{"id": f"p{n}", "fractie": "VVD", "fractie_id": "f-vvd", "actor": f"Lid {n}", "persoon_id": f"x{n}",
                   "stem": "Voor" if n < 12 else "Tegen", "fractiegrootte": 20, "vergissing": False} for n in range(20)]
    extra = [
        besluit("d1", "2026-05-12", "Brief regering", "Brief over huur", "Voor"),  # geen stemtype
        besluit("e1", "2022-01-01", "Motie", "Motie huur oud", "Voor"),  # buiten periode
        besluit("f1", "2026-06-01", "Motie", "Motie over fietspaden", "Voor", dossier="99999") | {"zaken": [
            {"id": "zf1", "nummer": "2026Zf1", "soort": "Motie", "titel": "Verkeer", "onderwerp": "Motie over fietspaden",
             "gestart_op": "2026-06-01", "volgnummer": 1, "dossiers": ["99999"]}]},  # geen zoekterm
        besluit("g1", "2026-06-02", "Motie", "Motie hoofdelijk huur", "Voor", dossier="11111", stemmingen=hoofdelijk),
    ]
    zet_pilot(werkmap, extra)
    assert v.main() == 0
    k = kandidaten(werkmap)
    assert k["selectie"]["aantal_treffers"] == 8
    assert k["selectie"]["peildatum"] == "2026-06-03T00:00:00Z"
    hk = [c for c in k["kandidaten"] if "hoofdelijk" in c["onderwerp"]][0]
    assert hk["partijstem"] == {"voor": 12, "tegen": 8, "niet_deelgenomen": 0, "vergissing": False}
    assert score(werkmap)["inzet"]["oordeel"] == "Onvoldoende bewijs"
    assert score(werkmap)["codering"]["ongecodeerd"] == 8


def test_dossier_match_en_subdossier(werkmap):
    schrijf_besluiten(werkmap, [besluit("a1", "2026-03-10", "Motie", "Motie zonder zoekterm", "Voor", dossier="21501-30")])
    schrijf(werkmap / "beloften" / "x.json", HUURBELOFTE | {"id": "x", "zoektermen": ["niets"], "dossiers": ["21501"]})
    assert v.main() == 0
    assert lees(werkmap / "data" / "kandidaten" / "x.json")["selectie"]["aantal_treffers"] == 1


def test_rekenvoorbeeld_uit_de_methode(werkmap):
    zet_pilot(werkmap)
    v.main()
    kand = kandidaten(werkmap)["kandidaten"]
    assert len(kand) == 7
    codeer_alles(werkmap, "ai", kand)
    codeer_alles(werkmap, "billy", kand)
    v.main()
    i = score(werkmap)["inzet"]
    assert i["oordeel"] == "Overwegend consistent"
    assert i["score"] == 0.6
    assert i["som_gewichten"] == 10
    assert (i["ruw_consistent"], i["ruw_totaal"]) == (2, 7)
    assert i["zonder_zwaarste_cluster"] == 0.2 and "onzeker" in i["markeringen"]
    assert i["alleen_wetten_en_amendementen"] == 0.625 and "selectiegevoelig" not in i["markeringen"]


def test_dubbele_codering_regels(werkmap):
    zet_pilot(werkmap)
    v.main()
    kand = kandidaten(werkmap)["kandidaten"]
    geschil = [k["sleutel"] for k in kand if "bevriezing 2" in k["onderwerp"]][0]
    vergeten = [k["sleutel"] for k in kand if "bevriezing 3" in k["onderwerp"]][0]

    # Eén codeur: niets telt mee.
    codeer_alles(werkmap, "billy", kand)
    v.main()
    c = score(werkmap)["codering"]
    assert c["een_codering"] == 7 and c["definitief"] == 0

    # AI codeert: eens op 5, oneens op 1 (uitsluiten), 1 vergeten.
    codeer_alles(werkmap, "ai", kand, behalve={geschil, vergeten})
    ai = lees(werkmap / "beoordelingen" / "vvd-2023-huur" / "codering-ai.json")
    ai["coderingen"][geschil] = {"opname": False, "reden_code": "U3"}
    schrijf(werkmap / "beoordelingen" / "vvd-2023-huur" / "codering-ai.json", ai)
    v.main()
    c = score(werkmap)["codering"]
    assert c == {"codeurs": ["ai", "billy"], "ongecodeerd": 0, "een_codering": 1, "geschil": 1, "definitief": 5}
    bt = lees(werkmap / "data" / "betrouwbaarheid.json")
    assert bt["totaal"]["ai / billy"] == {"n": 6, "kappa": 0.0}

    # Beslissing lost het geschil op; een tweede mens codeert de vergeten stemming.
    schrijf(werkmap / "beoordelingen" / "vvd-2023-huur" / "beslissingen.json",
            {geschil: {"opname": True, "richting_voorstem": "voor_belofte", "directheid": 1, "beslist_door": "billy"}})
    schrijf(werkmap / "beoordelingen" / "vvd-2023-huur" / "codering-anna.json",
            {"codeur": "anna", "coderingen": {vergeten: {"opname": True, "richting_voorstem": "voor_belofte", "directheid": 1}}})
    v.main()
    s = score(werkmap)
    assert s["codering"]["definitief"] == 7
    assert s["inzet"]["score"] == 0.6


def test_hoofdelijke_stemming_telt_naar_verhouding(werkmap):
    hoofdelijk = [{"id": f"p{n}", "fractie": "VVD", "fractie_id": "f-vvd", "actor": f"Lid {n}", "persoon_id": f"x{n}",
                   "stem": "Voor" if n < 12 else "Tegen", "fractiegrootte": 20, "vergissing": False} for n in range(20)]
    zet_pilot(werkmap, [besluit("g1", "2026-06-02", "Motie", "Motie hoofdelijk huur", "Voor", stemmingen=hoofdelijk)])
    v.main()
    kand = kandidaten(werkmap)["kandidaten"]
    hk = [k["sleutel"] for k in kand if "hoofdelijk" in k["onderwerp"]][0]
    for codeur in ("ai", "billy"):
        codeer_alles(werkmap, codeur, kand, behalve={hk})
        b = lees(werkmap / "beoordelingen" / "vvd-2023-huur" / f"codering-{codeur}.json")
        b["coderingen"][hk] = {"opname": True, "richting_voorstem": "tegen_belofte", "directheid": 0.5, "onderzoeksmotie": True}
        schrijf(werkmap / "beoordelingen" / "vvd-2023-huur" / f"codering-{codeur}.json", b)
    v.main()
    item = [x for x in score(werkmap)["opgenomen"] if x["sleutel"] == hk][0]
    assert item["c"] == 0.4, "8 van 20 stemden tegen, en 'tegen' is hier consistent"
    assert item["w"] == 0.25, "onderzoeksmotie 0,5 x directheid 0,5"
    assert abs(score(werkmap)["inzet"]["score"] - round((6 + 0.25 * 0.4) / 10.25, 3)) < 1e-9


def test_fouten_in_beoordeling_worden_gemeld(werkmap):
    zet_pilot(werkmap)
    v.main()
    kand = kandidaten(werkmap)["kandidaten"]
    codeer_alles(werkmap, "ai", kand)
    codeer_alles(werkmap, "billy", kand)
    schrijf(werkmap / "beoordelingen" / "vvd-2023-huur" / "beslissingen.json",
            {kand[0]["sleutel"]: {"opname": False}})  # uitsluiten zonder reden-code
    v.main()
    assert any("reden_code" in f for f in score(werkmap)["fouten"])


def test_resultaatoordeel_en_wederhoor(werkmap):
    zet_pilot(werkmap)
    v.main()
    assert score(werkmap)["resultaat"]["status"] == "nog niet geaccordeerd"
    schrijf(werkmap / "resultaten" / "vvd-2023-huur.json", {"oordeel": "niet_gerealiseerd", "wederhoor": False, "door": "billy"})
    v.main()
    assert score(werkmap)["resultaat"]["status"] == "wacht op wederhoor"
    schrijf(werkmap / "resultaten" / "vvd-2023-huur.json", {"oordeel": "deels_gerealiseerd", "door": "billy"})
    v.main()
    r = score(werkmap)["resultaat"]
    assert r["waarde"] == 0.5 and r["status"] == "geaccordeerd"
    schrijf(werkmap / "resultaten" / "vvd-2023-huur.json", {"oordeel": "onzin"})
    v.main()
    assert score(werkmap)["resultaat"]["oordeel"] is None


def test_rechtsstatelijke_toets_komt_in_score_en_rij(werkmap):
    zet_pilot(werkmap)
    toets = {"oordeel": "strijdig_grondwet", "grondslag": "art. 6 Gw", "label_publiek": "In strijd met de Grondwet."}
    schrijf(werkmap / "beloften" / "vvd-2023-huur.json", HUURBELOFTE | {"rechtsstatelijke_toets": toets})
    v.main()
    assert score(werkmap)["rechtsstatelijke_toets"] == toets
    assert lees(werkmap / "data" / "beoordelingsrij.json")[0]["rechtsstatelijk"] == "strijdig_grondwet"


def test_conceptbelofte_wordt_overgeslagen(werkmap):
    schrijf(werkmap / "beloften" / "vvd-2023-huur.json", HUURBELOFTE | {"status": "concept"})
    assert v.main() == 0
    assert not (werkmap / "data" / "kandidaten" / "vvd-2023-huur.json").exists()


def test_ongeldige_belofte_geeft_fout(werkmap):
    schrijf(werkmap / "beloften" / "kapot.json", {"id": "anders", "partij": "X"})
    assert v.main() == 1


@pytest.mark.parametrize("paren, verwacht", [
    ([("a", "a"), ("b", "b"), ("a", "b"), ("b", "b")], 0.5),
    ([("a", "a"), ("a", "a")], 1.0),
    ([], None),
])
def test_kappa(paren, verwacht):
    assert v.kappa(paren) == verwacht
