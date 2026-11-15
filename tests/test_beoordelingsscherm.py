"""Test van het beoordelingsscherm in een echte browser, tegen een nagebootste GitHub-API.

Wordt overgeslagen als Playwright niet is geinstalleerd:
    pip install playwright && playwright install chromium
"""
import base64
import json
import re
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

HTML = (Path(__file__).resolve().parent.parent / "beoordelen" / "index.html").read_text(encoding="utf-8")


def test_scherm_doorloopt_coderen_verschillen_resultaat(tmp_path):
    html = HTML
    K=[{"sleutel":f"b{i}:z{i}","datum":"2026-03-10","zaaknummer":f"2026Z0{i}","type":t,"titel":"Huurwet","onderwerp":o,"besluit":"Aangenomen.","partijstem":{"voor":22,"tegen":0,"niet_deelgenomen":0}}
       for i,(t,o) in enumerate([("wet","Wet betaalbare huur <script>alert(1)</script>"),("motie","Motie huurbevriezing"),("amendement","Amendement huurprijs")])]
    files={
     "beloften/vvd-2023-huur.json":{"id":"vvd-2023-huur","partij":"VVD","verkiezingsjaar":2023,"citaat":"Wij verlagen de huur","doel":"Huur omlaag","richting":"Stem voor lagere huur","kernelementen":["huur omlaag"],"horizon":"2027-12-31"},
     "data/kandidaten/vvd-2023-huur.json":{"selectie":{"zoektermen":["huur"],"dossiers":[],"peildatum":"2026-11-13"},"kandidaten":K},
     "data/scores/vvd-2023-huur.json":{"inzet":{"oordeel":"Onvoldoende bewijs"},"resultaat":{"oordeel":None,"status":"nog niet geaccordeerd"},"codering":{"codeurs":["ai"],"definitief":0,"geschil":0,"een_codering":3,"ongecodeerd":0}},
     "data/resultaat_suggesties/vvd-2023-huur.json":{"regel":{"oordeel":"loopt_nog","uitleg":"Wet aangenomen in TK.","feiten":{"horizon":"2027-12-31","horizon_verstreken":False,"wetten_voor_belofte_aangenomen_tk":["2026Z00"],"wetten_tegen_belofte_aangenomen_tk":[],"nog_te_beoordelen_stemmingen":3}},"ai":{"oordeel":"loopt_nog","onderbouwing":"In gang.","per_kernelement":[{"kernelement":"huur omlaag","stand":"in gang"}],"te_controleren":["Eerste Kamer"],"model":"m","op":"nu"}},
     "data/beoordelingsrij.json":[{"belofte_id":"vvd-2023-huur","partij":"VVD","kandidaten":3,"ongecodeerd":0,"een_codering":3,"geschil":0,"definitief":0,"inzet":"Onvoldoende bewijs","resultaat":None,"resultaat_status":"nog niet geaccordeerd"}],
     "data/betrouwbaarheid.json":{"totaal":{"ai / billy":{"n":6,"kappa":0.55}}},
     "beoordelingen/vvd-2023-huur/codering-ai.json":{"codeur":"ai","coderingen":{K[0]["sleutel"]:{"opname":True,"richting_voorstem":"voor_belofte","directheid":1,"toelichting":"ai zegt voor"},K[1]["sleutel"]:{"opname":False,"reden_code":"U3","toelichting":"ai twijfelt"},K[2]["sleutel"]:{"opname":True,"richting_voorstem":"tegen_belofte","directheid":1}}},
    }
    puts=[]; fouten=[]
    def handler(route):
        req=route.request; u=req.url
        if u.startswith("https://kiwis92.github.io"): return route.fulfill(status=200,content_type="text/html",body=html)
        if not u.startswith("https://api.github.com"): return route.abort()
        assert req.headers.get("authorization")=="Bearer geheim", req.headers
        if u.endswith("/user"): return route.fulfill(json={"login":"billy"})
        m=re.match(r"https://api\.github\.com/repos/kiwis92/PoliTrack/contents/([^?]+)",u); pad=m.group(1)
        if req.method=="PUT":
            body=json.loads(req.post_data); inhoud=json.loads(base64.b64decode(body["content"]).decode("utf-8")); files[pad]=inhoud; puts.append((pad,body["message"],body.get("sha"),body["branch"]))
            return route.fulfill(status=200,json={"content":{"sha":"nieuw"}})
        if pad in ("beloften","beoordelingen/vvd-2023-huur"):
            return route.fulfill(json=[{"name":p.split("/")[-1]} for p in files if p.startswith(pad+"/")]+([{"name":"_voorbeeld.json"}] if pad=="beloften" else []))
        if pad not in files: return route.fulfill(status=404,json={"message":"Not Found"})
        tekst=json.dumps(files[pad],ensure_ascii=False)
        if "raw" in req.headers.get("accept",""): return route.fulfill(status=200,body=tekst,content_type="text/plain; charset=utf-8")
        return route.fulfill(json={"sha":"oud","content":base64.b64encode(tekst.encode()).decode()})
    with playwright.sync_playwright() as p:
        br=p.chromium.launch(); pg=br.new_page(viewport={"width":1100,"height":900})
        pg.on("pageerror",lambda e: fouten.append(str(e))); pg.on("console",lambda m: fouten.append(m.text) if m.type=="error" and "404" not in m.text else None)
        pg.on("dialog",lambda d: (fouten.append("dialog:"+d.message), d.dismiss()))
        pg.route("**/*",handler); pg.goto("https://kiwis92.github.io/PoliTrack/beoordelen/")
        assert pg.input_value("#repo")=="kiwis92/PoliTrack"
        pg.fill("#token","geheim"); pg.click("#login"); pg.wait_for_selector("#paneel form")
        assert "Ingelogd als billy" in pg.inner_text("#wie") and pg.input_value("#token")==""
        assert pg.locator("#belofte option").count()==1
        t=pg.inner_text("#paneel"); assert "3 van 3" in t and "ai zegt" not in t and "22 voor" not in t, t   # blind
        assert "<script>alert(1)</script>" in t   # als tekst getoond, niet uitgevoerd
        pg.screenshot(path=str(tmp_path / "coderen.png"),full_page=True)
        # 1: opnemen voor_belofte (eens met AI)
        pg.check("#paneel input[value=true]"); pg.select_option("#paneel form select >> nth=0","voor_belofte"); pg.click("#paneel form button[type=submit]")
        # 2: opnemen tegen (AI: uitsluiten) -> geschil ; eerst validatie testen
        pg.check("#paneel input[value=true]"); pg.click("#paneel form button[type=submit]"); assert "Kies een richting" in pg.inner_text("#melding")
        pg.select_option("#paneel form select >> nth=0","tegen_belofte"); pg.click("#paneel form button[type=submit]")
        # 3: uitsluiten U4 (AI: opnemen tegen) -> geschil
        pg.check("#paneel input[value=false]"); pg.select_option("#paneel form select >> nth=2","U4"); pg.fill("#paneel textarea","pakket"); pg.click("#paneel form button[type=submit]")
        assert "Niets meer te coderen" in pg.inner_text("#paneel")
        pg.click("text=Opslaan in repo (3)"); pg.wait_for_selector("#melding.goed")
        pad,msg,sha,tak=puts[-1]; assert pad=="beoordelingen/vvd-2023-huur/codering-billy.json" and sha is None and tak=="master", puts[-1]
        mijn=files[pad]; assert mijn["codeur"]=="billy" and len(mijn["coderingen"])==3 and mijn["coderingen"][K[2]["sleutel"]]=={**mijn["coderingen"][K[2]["sleutel"]],"opname":False,"reden_code":"U4","toelichting":"pakket"}
        # verschillen
        pg.click("nav.tabs button[data-tab=verschillen]"); t=pg.inner_text("#paneel"); assert "2 stemmingen waar de codeurs verschillen" in t and "ai twijfelt" in t and "22 voor" in t, t
        pg.screenshot(path=str(tmp_path / "verschillen.png"),full_page=True)
        assert pg.is_checked("#paneel input[value=true]")   # vooringevuld met mijn codering
        pg.click("#paneel form button[type=submit]"); pg.click("#paneel form button[type=submit]")
        pg.click("text=Opslaan in repo (2)"); pg.wait_for_selector("#melding.goed")
        assert puts[-1][0]=="beoordelingen/vvd-2023-huur/beslissingen.json" and len(files[puts[-1][0]])==2 and all(x["beslist_door"]=="billy" for x in files[puts[-1][0]].values())
        assert "Geen openstaande verschillen" in pg.inner_text("#paneel")
        # resultaat
        pg.click("nav.tabs button[data-tab=resultaat]"); t=pg.inner_text("#paneel"); assert "Eerste Kamer" in t and "Vaste regels: Loopt nog" in t
        assert pg.input_value("#paneel select")=="loopt_nog"
        pg.select_option("#paneel select","niet_gerealiseerd"); pg.click("text=Accorderen en opslaan"); assert "toelichting en minstens één bron" in pg.inner_text("#melding")
        ta=pg.locator("#paneel textarea"); ta.nth(0).fill("Horizon verstreken."); ta.nth(1).fill("https://voorbeeld.nl/a\n36000")
        pg.click("text=Accorderen en opslaan"); pg.wait_for_selector("#melding.goed"); assert "wederhoor" in pg.inner_text("#melding")
        r=files["resultaten/vvd-2023-huur.json"]; assert r["oordeel"]=="niet_gerealiseerd" and r["bronnen"]==["https://voorbeeld.nl/a","36000"] and r["wederhoor"] is False and r["door"]=="billy"
        pg.screenshot(path=str(tmp_path / "resultaat.png"),full_page=True)
        pg.click("nav.tabs button[data-tab=overzicht]"); t=pg.inner_text("#paneel"); assert "0,55" in t and "onder de streefwaarde" in t and "vvd-2023-huur" in t
        pg.screenshot(path=str(tmp_path / "overzicht.png"),full_page=True)
        # smal scherm
        pg.set_viewport_size({"width":380,"height":800}); pg.click("nav.tabs button[data-tab=resultaat]")
        assert pg.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1")
        pg.screenshot(path=str(tmp_path / "mobiel.png"))
        br.close()
    assert not fouten, fouten
    assert [x[0] for x in puts] == ["beoordelingen/vvd-2023-huur/codering-billy.json", "beoordelingen/vvd-2023-huur/beslissingen.json", "resultaten/vvd-2023-huur.json"]
