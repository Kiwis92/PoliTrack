"""Tests voor het ophalen van stemmingen, met een nagebootste API."""
import urllib.parse

import sync_stemmingen as s
from conftest import lees

B1 = "ef4bea4a-0ac9-4dab-9a30-ee9c59adcdf2"
B2 = "aa000000-0000-0000-0000-000000000001"


def api_besluit(i, stemmen, verwijderd=False):
    return {
        "Id": i, "StemmingsSoort": "Met handopsteken", "BesluitSoort": "Stemmen - aangenomen",
        "BesluitTekst": "Aangenomen.", "Status": "Besluit", "Verwijderd": verwijderd,
        "Zaak": [{"Id": "z1", "Nummer": "2026Z19641", "Soort": "Motie", "Titel": "T", "Onderwerp": "O",
                  "GestartOp": "2026-09-23T00:00:00+02:00", "Volgnummer": 713,
                  "Kamerstukdossier": [{"Nummer": 21501, "Toevoeging": "30"}, {"Nummer": 36410, "Toevoeging": None}]}],
        "Stemming": stemmen,
        "Agendapunt": {"Id": "a", "Activiteit": {"Id": "x", "Datum": "2026-09-23T13:30:00+02:00", "Soort": "Stemmingen"}},
    }


def api_stem(i, fractie, soort, verwijderd=False):
    return {"Id": i, "Soort": soort, "ActorNaam": fractie, "ActorFractie": fractie, "FractieGrootte": 3,
            "Vergissing": False, "Persoon_Id": None, "Fractie_Id": "f" + i, "Verwijderd": verwijderd}


class NepApi:
    """Twee rondes: in ronde 2 is besluit B2 uit de API verdwenen."""

    def __init__(self):
        self.ronde = 1
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        u = urllib.parse.unquote(url)
        if "/Stemming?" in u or u == "VOLGENDE":
            if u == "VOLGENDE":
                return {"value": [{"Besluit_Id": B2, "ApiGewijzigdOp": "2026-11-13T12:00:00Z"}]}
            if self.ronde == 1:
                return {"value": [{"Besluit_Id": B1, "ApiGewijzigdOp": "2026-11-13T11:59:00.204475Z"}],
                        "@odata.nextLink": "VOLGENDE"}
            return {"value": [{"Besluit_Id": B2, "ApiGewijzigdOp": "2026-11-14T00:00:00Z"}]}
        if B1 in u:
            return {"value": [api_besluit(B1, [api_stem("2", "VVD", "Voor"), api_stem("1", "SP", "Tegen"),
                                                api_stem("3", "X", "Voor", verwijderd=True)])]}
        if self.ronde == 1:
            return {"value": [api_besluit(B2, [api_stem("9", "PVV", "Voor")])]}
        return {"value": []}


def test_sync_schrijft_besluiten_en_hervat(werkmap):
    api = NepApi()
    state = s.sync(haal=api)

    f1 = lees(s.pad_voor(B1))
    assert [x["fractie"] for x in f1["stemmingen"]] == ["SP", "VVD"], "verwijderde stem weg, rest gesorteerd"
    assert f1["datum"].startswith("2026-09-23")
    assert f1["zaken"][0]["soort"] == "Motie"
    assert f1["zaken"][0]["dossiers"] == ["21501-30", "36410"]
    assert s.pad_voor(B2).exists()
    assert state["watermerk"] == "2026-11-13T12:00:00Z"
    assert state["laatste_run_geschreven"] == 2
    assert "ge%202023-12-06T00%3A00%3A00Z" in api.urls[0], "eerste run begint bij de standaarddatum"

    api.ronde = 2
    n = len(api.urls)
    state = s.sync(haal=api)
    assert "ge%202026-11-13T12%3A00%3A00Z" in api.urls[n], "tweede run gaat verder bij het watermerk"
    assert not s.pad_voor(B2).exists(), "besluit dat de API niet meer kent wordt lokaal verwijderd"
    assert state["laatste_run_verwijderd"] == 1


def test_url_voor_laat_odata_tekens_staan():
    url = s.url_voor("Besluit", "$filter=Id eq abc&$expand=Zaak($select=Id)")
    assert url.endswith("Besluit?$filter=Id%20eq%20abc&$expand=Zaak($select=Id)")
