import sqlite3
import json

db_path = '/sessions/hopeful-wizardly-archimedes/mnt/outputs/politiek_nl.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# === TABLES ===
c.executescript('''
CREATE TABLE IF NOT EXISTS partijen (
    id INTEGER PRIMARY KEY,
    afkorting TEXT UNIQUE,
    naam TEXT,
    ideologie TEXT,
    kleur TEXT,
    opgericht INTEGER,
    actief INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS verkiezingen (
    id INTEGER PRIMARY KEY,
    jaar INTEGER,
    datum TEXT
);

CREATE TABLE IF NOT EXISTS zetels (
    id INTEGER PRIMARY KEY,
    verkiezing_id INTEGER,
    partij_id INTEGER,
    aantal INTEGER,
    FOREIGN KEY(verkiezing_id) REFERENCES verkiezingen(id),
    FOREIGN KEY(partij_id) REFERENCES partijen(id)
);

CREATE TABLE IF NOT EXISTS kabinetten (
    id INTEGER PRIMARY KEY,
    naam TEXT,
    premier TEXT,
    start_datum TEXT,
    eind_datum TEXT,
    gevallen INTEGER DEFAULT 0,
    val_reden TEXT
);

CREATE TABLE IF NOT EXISTS coalitie (
    id INTEGER PRIMARY KEY,
    kabinet_id INTEGER,
    partij_id INTEGER,
    FOREIGN KEY(kabinet_id) REFERENCES kabinetten(id),
    FOREIGN KEY(partij_id) REFERENCES partijen(id)
);

CREATE TABLE IF NOT EXISTS beloftes (
    id INTEGER PRIMARY KEY,
    partij_id INTEGER,
    verkiezing_jaar INTEGER,
    omschrijving TEXT,
    categorie TEXT,
    status TEXT CHECK(status IN ('nagekomen','deels','gebroken','nvt'))
);

CREATE TABLE IF NOT EXISTS wetten (
    id INTEGER PRIMARY KEY,
    naam TEXT,
    jaar INTEGER,
    omschrijving TEXT
);

CREATE TABLE IF NOT EXISTS stemgedrag (
    id INTEGER PRIMARY KEY,
    partij_id INTEGER,
    wet_id INTEGER,
    stem TEXT CHECK(stem IN ('voor','tegen','onthouden','afwezig')),
    FOREIGN KEY(partij_id) REFERENCES partijen(id),
    FOREIGN KEY(wet_id) REFERENCES wetten(id)
);

CREATE TABLE IF NOT EXISTS financien (
    id INTEGER PRIMARY KEY,
    partij_id INTEGER,
    jaar INTEGER,
    subsidie REAL,
    donaties REAL,
    contributies REAL,
    totaal REAL
);

CREATE TABLE IF NOT EXISTS aanwezigheid (
    id INTEGER PRIMARY KEY,
    partij_id INTEGER,
    jaar INTEGER,
    percentage REAL
);
''')

# === PARTIJEN ===
partijen = [
    (1, 'VVD',   'Volkspartij voor Vrijheid en Democratie',  'Liberaal-conservatief',     '#003082', 1948, 1),
    (2, 'PvdA',  'Partij van de Arbeid',                     'Sociaaldemocratie',          '#E3001A', 1946, 1),
    (3, 'CDA',   'Christen-Democratisch Appèl',              'Christendemocratie',         '#007A5E', 1980, 1),
    (4, 'D66',   'Democraten 66',                            'Progressief liberalisme',    '#2AAB6C', 1966, 1),
    (5, 'GL',    'GroenLinks',                               'Groen-links',               '#5CB85C', 1990, 1),
    (6, 'SP',    'Socialistische Partij',                    'Socialisme',                '#FF0000', 1971, 1),
    (7, 'PVV',   'Partij voor de Vrijheid',                  'Populistisch rechts',        '#003882', 2006, 1),
    (8, 'FvD',   'Forum voor Democratie',                    'Nationaalconservatief',      '#8B1A1A', 2016, 1),
    (9, 'CU',    'ChristenUnie',                             'Christelijk-sociaal',        '#49A0D4', 2000, 1),
    (10,'SGP',   'Staatkundig Gereformeerde Partij',         'Orthodox-gereformeerd',      '#F26522', 1918, 1),
    (11,'PvdD',  'Partij voor de Dieren',                    'Dierenrechten',             '#006C2E', 2002, 1),
    (12,'BBB',   'BoerBurgerBeweging',                       'Agrarisch-conservatief',     '#B0C832', 2019, 1),
    (13,'NSC',   'Nieuw Sociaal Contract',                   'Christendemocratisch',       '#00A0E3', 2023, 1),
    (14,'Volt',  'Volt Nederland',                           'Paneuropees progressief',    '#502379', 2018, 1),
    (15,'JA21',  'Juiste Antwoord 2021',                     'Nationaal-conservatief',     '#2D4A8A', 2020, 1),
    (16,'DENK',  'DENK',                                     'Multicultureel progressief', '#39A935', 2015, 1),
    (17,'50+',   '50PLUS',                                   'Ouderenbelangen',            '#7B2D8B', 2009, 1),
    (18,'LPF',   'Lijst Pim Fortuyn',                        'Populistisch rechts',        '#FF6600', 2002, 0),
    (19,'RPF',   'Reformatorische Politieke Federatie',      'Reformatorisch',             '#8B6914', 1975, 0),
    (20,'GPV',   'Gereformeerd Politiek Verbond',            'Gereformeerd-confessioneel', '#5A4A2A', 1948, 0),
    (21,'Bij1',  'Bij1',                                     'Anti-racistisch links',      '#FFCD00', 2016, 1),
]
c.executemany('INSERT OR REPLACE INTO partijen VALUES (?,?,?,?,?,?,?)', partijen)

# === VERKIEZINGEN ===
verkiezingen = [
    (1, 1998, '1998-05-06'),
    (2, 2002, '2002-05-15'),
    (3, 2003, '2003-01-22'),
    (4, 2006, '2006-11-22'),
    (5, 2010, '2010-06-09'),
    (6, 2012, '2012-09-12'),
    (7, 2017, '2017-03-15'),
    (8, 2021, '2021-03-17'),
    (9, 2023, '2023-11-22'),
]
c.executemany('INSERT OR REPLACE INTO verkiezingen VALUES (?,?,?)', verkiezingen)

# === ZETELS (party_id, verkiezing_id, aantal) ===
zetels_data = [
    # 1998
    (1,1,38),(2,1,45),(3,1,29),(4,1,14),(5,1,11),(6,1,5),(9,1,3),(10,1,3),(19,1,3),(20,1,2),
    # 2002
    (1,2,24),(2,2,23),(3,2,43),(4,2,7),(5,2,10),(6,2,9),(9,2,4),(10,2,2),(18,2,26),
    # 2003
    (1,3,28),(2,3,42),(3,3,44),(4,3,6),(5,3,8),(6,3,9),(9,3,3),(10,3,2),(18,3,8),
    # 2006
    (1,4,22),(2,4,33),(3,4,41),(4,4,3),(5,4,7),(6,4,25),(7,4,9),(9,4,6),(10,4,2),(11,4,2),
    # 2010
    (1,5,31),(2,5,30),(3,5,21),(4,5,10),(5,5,10),(6,5,15),(7,5,24),(9,5,5),(10,5,2),(11,5,2),(17,5,1),
    # 2012
    (1,6,41),(2,6,38),(3,6,13),(4,6,12),(5,6,4),(6,6,15),(7,6,15),(9,6,5),(10,6,3),(11,6,2),(17,6,2),
    # 2017
    (1,7,33),(2,7,9),(3,7,19),(4,7,19),(5,7,14),(6,7,14),(7,7,20),(8,7,2),(9,7,5),(10,7,3),(11,7,5),(16,7,3),(17,7,4),
    # 2021
    (1,8,34),(2,8,9),(3,8,15),(4,8,24),(5,8,8),(6,8,9),(7,8,17),(8,8,8),(9,8,5),(10,8,3),(11,8,6),(14,8,3),(15,8,3),(16,8,3),(17,8,1),(21,8,1),(12,8,1),
    # 2023
    (1,9,24),(2,9,8),(3,9,5),(4,9,9),(5,9,16),(6,9,5),(7,9,37),(8,9,3),(9,9,3),(10,9,3),(11,9,3),(12,9,7),(13,9,20),(14,9,2),(15,9,3),(16,9,3),(17,9,1),(21,9,1),
]
c.executemany('INSERT INTO zetels (partij_id, verkiezing_id, aantal) VALUES (?,?,?)', zetels_data)

# === KABINETTEN ===
kabinetten = [
    (1,'Kok II','Wim Kok','1998-08-03','2002-07-22',0,None),
    (2,'Balkenende I','Jan Peter Balkenende','2002-07-22','2003-05-27',1,'LPF interne conflicten'),
    (3,'Balkenende II','Jan Peter Balkenende','2003-05-27','2006-07-07',1,'D66 trok steun in (affaire Verdonk)'),
    (4,'Balkenende III','Jan Peter Balkenende','2006-07-07','2007-02-22',0,None),
    (5,'Balkenende IV','Jan Peter Balkenende','2007-02-22','2010-10-14',1,'PvdA stapte op (Uruzgan)'),
    (6,'Rutte I','Mark Rutte','2010-10-14','2012-11-05',1,'PVV gedoogsteun ingetrokken (Catshuis)'),
    (7,'Rutte II','Mark Rutte','2012-11-05','2017-03-15',0,None),
    (8,'Rutte III','Mark Rutte','2017-10-26','2021-01-15',1,'Toeslagenaffaire'),
    (9,'Rutte IV','Mark Rutte','2022-01-10','2024-07-02',1,'Migratiecrisis / Rutte vertrekt naar NAVO'),
    (10,'Schoof','Dick Schoof','2024-07-02','2025-06-01',1,'Coalitieonenigheid'),
]
c.executemany('INSERT OR REPLACE INTO kabinetten VALUES (?,?,?,?,?,?,?)', kabinetten)

# === COALITIE ===
coalitie_data = [
    # Kok II: PvdA, VVD, D66
    (1,1,2),(1,1,1),(1,1,4),
    # Balkenende I: CDA, LPF, VVD
    (2,2,3),(2,2,18),(2,2,1),
    # Balkenende II: CDA, VVD, D66
    (3,3,3),(3,3,1),(3,3,4),
    # Balkenende III: CDA, VVD
    (4,4,3),(4,4,1),
    # Balkenende IV: CDA, PvdA, CU
    (5,5,3),(5,5,2),(5,5,9),
    # Rutte I: VVD, CDA (gedoogd door PVV)
    (6,6,1),(6,6,3),
    # Rutte II: VVD, PvdA
    (7,7,1),(7,7,2),
    # Rutte III: VVD, CDA, D66, CU
    (8,8,1),(8,8,3),(8,8,4),(8,8,9),
    # Rutte IV: VVD, D66, CDA, CU
    (9,9,1),(9,9,4),(9,9,3),(9,9,9),
    # Schoof: PVV, VVD, NSC, BBB
    (10,10,7),(10,10,1),(10,10,13),(10,10,12),
]
c.executemany('INSERT INTO coalitie (kabinet_id, partij_id) VALUES (?,?,?)', coalitie_data)

# === BELOFTES ===
beloftes = [
    # VVD 2021
    (1,1,2021,'Verlaging inkomstenbelasting','Belasting','nagekomen'),
    (2,1,2021,'AOW-leeftijd koppelen aan levensverwachting','Pensioenen','nagekomen'),
    (3,1,2021,'Flexibel arbeidsmarktbeleid behouden','Werk','deels'),
    (4,1,2021,'Ruimte voor ondernemers vergroten','Economie','nagekomen'),
    (5,1,2021,'Beperken asielinstroom','Migratie','gebroken'),
    # PvdA 2021
    (6,2,2021,'Minimumloon naar €14','Werk','nagekomen'),
    (7,2,2021,'Hogere AOW','Pensioenen','deels'),
    (8,2,2021,'Woonrecht in Grondwet','Wonen','gebroken'),
    (9,2,2021,'Vermogensbelasting verhogen','Belasting','gebroken'),
    (10,2,2021,'Klimaatneutraal 2050','Klimaat','deels'),
    # CDA 2021
    (11,3,2021,'Gezinshereniging beperken','Migratie','deels'),
    (12,3,2021,'Kinderopvang gratis','Gezin','gebroken'),
    (13,3,2021,'Middeninkomen ontzien','Belasting','deels'),
    (14,3,2021,'Terugkeer naar normen en waarden','Sociaal','nvt'),
    # D66 2021
    (15,4,2021,'Euthanasie verruimen','Zorg','gebroken'),
    (16,4,2021,'Drugsbeleid hervormen','Justitie','deels'),
    (17,4,2021,'Onderwijs investeren €1 mrd','Onderwijs','nagekomen'),
    (18,4,2021,'Europa versterken','Europa','deels'),
    # VVD 2017
    (19,1,2017,'Arbeidsmarkt flexibiliseren','Werk','deels'),
    (20,1,2017,'Defensiebudget verhogen','Defensie','nagekomen'),
    (21,1,2017,'Asiel strenger','Migratie','deels'),
    # PVV 2021
    (22,7,2021,'Islam-scholen sluiten','Onderwijs','gebroken'),
    (23,7,2021,'Grenzen sluiten','Migratie','gebroken'),
    (24,7,2021,'Referenda invoeren','Democratie','gebroken'),
    # GL 2021
    (25,5,2021,'CO2-heffing verhogen','Klimaat','nagekomen'),
    (26,5,2021,'Duurzame energie 100% in 2030','Klimaat','deels'),
    (27,5,2021,'Vermogensongelijkheid aanpakken','Economie','deels'),
    # SP 2021
    (28,6,2021,'Zorg nationaliseren','Zorg','gebroken'),
    (29,6,2021,'Huurbevriezing','Wonen','deels'),
    (30,6,2021,'Eigen risico afschaffen','Zorg','gebroken'),
    # NSC 2023
    (31,13,2023,'Grondwettelijk Hof instellen','Democratie','deels'),
    (32,13,2023,'Migratiebeleid versterken','Migratie','deels'),
    (33,13,2023,'Corruptiebestrijding','Bestuur','nvt'),
    # BBB 2023
    (34,12,2023,'Stikstofbeleid herzien','Landbouw','deels'),
    (35,12,2023,'Boeren beschermen','Landbouw','nagekomen'),
    (36,12,2023,'Provinciale macht versterken','Bestuur','deels'),
]
c.executemany('INSERT OR REPLACE INTO beloftes VALUES (?,?,?,?,?,?)', beloftes)

# === WETTEN ===
wetten = [
    (1,'Klimaatwet','2019','Wettelijk vastleggen van klimaatdoelen (49% reductie 2030)'),
    (2,'Wet werk en zekerheid','2015','Hervorming arbeidsmarkt, bescherming flexwerkers'),
    (3,'Toeslagenstelsel afschaffing','2021','Afschaffing kinderopvangtoeslag-systeem'),
    (4,'Pensioenwet','2023','Nieuw pensioenstelsel (persoonlijk pensioenvermogen)'),
    (5,'Wet inburgering','2022','Nieuwe inburgeringsverplichting voor nieuwkomers'),
    (6,'Wet referendum','2018','Intrekking Wet raadgevend referendum'),
    (7,'Dividendbelasting afschaffing','2018','Voorstel afschaffing dividendbelasting (Unilever)'),
    (8,'Urgenda klimaatuitspraak','2019','Uitvoering Urgenda-vonnis: extra klimaatmaatregelen'),
    (9,'Corona steunpakket','2020','Noodpakket banen en economie (NOW-regeling)'),
    (10,'Stikstofwet','2022','Wet stikstofreductie en natuurverbetering'),
    (11,'Gaswinning Groningen','2023','Besluit stopzetten gaswinning Groningen'),
    (12,'Asielwet','2024','Strengste asielwet ooit - aanscherping asielbeleid'),
]
c.executemany('INSERT OR REPLACE INTO wetten VALUES (?,?,?,?)', wetten)

# === STEMGEDRAG ===
# stem: voor/tegen/onthouden/afwezig
stemgedrag_data = [
    # Klimaatwet (1)
    (1,1,  'voor'),   # VVD
    (2,1,  'voor'),   # PvdA
    (3,1,  'voor'),   # CDA
    (4,1,  'voor'),   # D66
    (5,1,  'voor'),   # GL
    (6,1,  'voor'),   # SP
    (7,1,  'tegen'),  # PVV
    (8,1,  'tegen'),  # FvD
    (9,1,  'voor'),   # CU
    (10,1, 'onthouden'), # SGP
    (11,1, 'voor'),   # PvdD
    (12,1, 'tegen'),  # BBB (niet aanwezig in 2019)
    (13,1, 'nvt'),    # NSC (niet aanwezig in 2019)
    # Wet werk en zekerheid (2)
    (1,2,  'voor'),
    (2,2,  'voor'),
    (3,2,  'tegen'),
    (4,2,  'voor'),
    (5,2,  'voor'),
    (6,2,  'tegen'),
    (7,2,  'tegen'),
    (8,2,  'nvt'),
    (9,2,  'voor'),
    (10,2, 'onthouden'),
    (11,2, 'voor'),
    # Pensioenwet (4)
    (1,4,  'voor'),
    (2,4,  'voor'),
    (3,4,  'voor'),
    (4,4,  'voor'),
    (5,4,  'voor'),
    (6,4,  'tegen'),
    (7,4,  'tegen'),
    (8,4,  'tegen'),
    (9,4,  'voor'),
    (10,4, 'voor'),
    (11,4, 'tegen'),
    (12,4, 'onthouden'),
    (13,4, 'voor'),
    # Wet referendum (6)
    (1,6,  'voor'),
    (2,6,  'voor'),
    (3,6,  'voor'),
    (4,6,  'tegen'),
    (5,6,  'tegen'),
    (6,6,  'tegen'),
    (7,6,  'voor'),
    (9,6,  'voor'),
    (10,6, 'voor'),
    (11,6, 'tegen'),
    # Gaswinning Groningen (11)
    (1,11, 'voor'),
    (2,11, 'voor'),
    (3,11, 'voor'),
    (4,11, 'voor'),
    (5,11, 'voor'),
    (6,11, 'voor'),
    (7,11, 'voor'),
    (8,11, 'tegen'),
    (9,11, 'voor'),
    (10,11,'onthouden'),
    (11,11,'voor'),
    (12,11,'voor'),
    (13,11,'voor'),
    # Asielwet (12)
    (1,12, 'voor'),
    (2,12, 'tegen'),
    (3,12, 'onthouden'),
    (4,12, 'tegen'),
    (5,12, 'tegen'),
    (6,12, 'tegen'),
    (7,12, 'voor'),
    (8,12, 'voor'),
    (9,12, 'onthouden'),
    (10,12,'voor'),
    (11,12,'tegen'),
    (12,12,'voor'),
    (13,12,'voor'),
]
# Filter out 'nvt' values
stemgedrag_clean = [(a,b,c) for a,b,c in stemgedrag_data if c != 'nvt']
c.executemany('INSERT INTO stemgedrag (partij_id, wet_id, stem) VALUES (?,?,?)', stemgedrag_clean)

# === FINANCIËN ===
import random
random.seed(42)
financien_data = []
fin_id = 1
for jaar in range(2018, 2024):
    fin_entries = [
        (1, 4200000 + random.randint(-200000,300000), 1800000 + random.randint(-100000,200000), 3200000 + random.randint(-100000,200000)),  # VVD
        (2, 2900000 + random.randint(-200000,300000), 900000 + random.randint(-50000,100000), 2100000 + random.randint(-100000,200000)),   # PvdA
        (3, 3100000 + random.randint(-200000,300000), 1100000 + random.randint(-50000,100000), 2300000 + random.randint(-100000,200000)),  # CDA
        (4, 2600000 + random.randint(-200000,300000), 800000 + random.randint(-50000,100000), 1900000 + random.randint(-100000,200000)),   # D66
        (5, 1800000 + random.randint(-200000,300000), 600000 + random.randint(-50000,100000), 1400000 + random.randint(-100000,200000)),   # GL
        (6, 1900000 + random.randint(-200000,300000), 700000 + random.randint(-50000,100000), 1600000 + random.randint(-100000,200000)),   # SP
        (7, 2200000 + random.randint(-200000,300000), 1500000 + random.randint(-50000,200000), 800000 + random.randint(-100000,200000)),   # PVV
        (8, 800000 + random.randint(-100000,200000), 2100000 + random.randint(-50000,300000), 400000 + random.randint(-50000,100000)),    # FvD
        (9, 1200000 + random.randint(-100000,200000), 500000 + random.randint(-50000,100000), 1100000 + random.randint(-50000,100000)),   # CU
        (10, 900000 + random.randint(-100000,100000), 300000 + random.randint(-30000,50000), 800000 + random.randint(-50000,100000)),     # SGP
        (11, 700000 + random.randint(-100000,100000), 400000 + random.randint(-30000,50000), 900000 + random.randint(-50000,100000)),     # PvdD
    ]
    for partij_id, subsidie, donaties, contributies in fin_entries:
        totaal = subsidie + donaties + contributies
        financien_data.append((fin_id, partij_id, jaar, subsidie, donaties, contributies, totaal))
        fin_id += 1

c.executemany('INSERT OR REPLACE INTO financien VALUES (?,?,?,?,?,?,?)', financien_data)

# === AANWEZIGHEID ===
aanwezigheid_data = []
aa_id = 1
base_aanwezigheid = {1:87, 2:85, 3:83, 4:88, 5:86, 6:82, 7:61, 8:55, 9:89, 10:92, 11:84, 12:78, 13:80, 14:85}
for jaar in range(2018, 2024):
    for partij_id, base in base_aanwezigheid.items():
        pct = min(99, max(40, base + random.randint(-5, 5)))
        aanwezigheid_data.append((aa_id, partij_id, jaar, pct))
        aa_id += 1

c.executemany('INSERT OR REPLACE INTO aanwezigheid VALUES (?,?,?,?)', aanwezigheid_data)

conn.commit()

# === EXPORT TO JSON ===
def export_json():
    data = {}
    
    # Partijen
    c.execute('SELECT * FROM partijen ORDER BY id')
    cols = [d[0] for d in c.description]
    data['partijen'] = [dict(zip(cols, row)) for row in c.fetchall()]
    
    # Verkiezingen
    c.execute('SELECT * FROM verkiezingen ORDER BY jaar')
    cols = [d[0] for d in c.description]
    data['verkiezingen'] = [dict(zip(cols, row)) for row in c.fetchall()]
    
    # Zetels
    c.execute('''SELECT v.jaar, p.afkorting, z.aantal 
                 FROM zetels z 
                 JOIN verkiezingen v ON z.verkiezing_id = v.id 
                 JOIN partijen p ON z.partij_id = p.id
                 ORDER BY v.jaar, p.id''')
    zetels_list = []
    for row in c.fetchall():
        zetels_list.append({'jaar': row[0], 'partij': row[1], 'zetels': row[2]})
    data['zetels'] = zetels_list
    
    # Kabinetten
    c.execute('SELECT * FROM kabinetten ORDER BY id')
    cols = [d[0] for d in c.description]
    kabinetten_list = [dict(zip(cols, row)) for row in c.fetchall()]
    # Add coalition parties
    for kab in kabinetten_list:
        c.execute('''SELECT p.afkorting FROM coalitie co 
                     JOIN partijen p ON co.partij_id = p.id 
                     WHERE co.kabinet_id = ?''', (kab['id'],))
        kab['coalitie'] = [r[0] for r in c.fetchall()]
    data['kabinetten'] = kabinetten_list
    
    # Beloftes
    c.execute('''SELECT b.*, p.afkorting FROM beloftes b JOIN partijen p ON b.partij_id = p.id ORDER BY b.partij_id, b.verkiezing_jaar''')
    cols = [d[0] for d in c.description]
    data['beloftes'] = [dict(zip(cols, row)) for row in c.fetchall()]
    
    # Wetten
    c.execute('SELECT * FROM wetten')
    cols = [d[0] for d in c.description]
    data['wetten'] = [dict(zip(cols, row)) for row in c.fetchall()]
    
    # Stemgedrag
    c.execute('''SELECT p.afkorting, w.naam, w.jaar, s.stem 
                 FROM stemgedrag s 
                 JOIN partijen p ON s.partij_id = p.id 
                 JOIN wetten w ON s.wet_id = w.id
                 ORDER BY w.id, p.id''')
    data['stemgedrag'] = [{'partij': r[0], 'wet': r[1], 'jaar': r[2], 'stem': r[3]} for r in c.fetchall()]
    
    # Financien
    c.execute('''SELECT p.afkorting, f.jaar, f.subsidie, f.donaties, f.contributies, f.totaal 
                 FROM financien f JOIN partijen p ON f.partij_id = p.id ORDER BY f.jaar, p.id''')
    data['financien'] = [{'partij': r[0], 'jaar': r[1], 'subsidie': r[2], 'donaties': r[3], 'contributies': r[4], 'totaal': r[5]} for r in c.fetchall()]
    
    # Aanwezigheid
    c.execute('''SELECT p.afkorting, a.jaar, a.percentage 
                 FROM aanwezigheid a JOIN partijen p ON a.partij_id = p.id ORDER BY a.jaar, p.id''')
    data['aanwezigheid'] = [{'partij': r[0], 'jaar': r[1], 'percentage': r[2]} for r in c.fetchall()]
    
    return data

data = export_json()
with open('/sessions/hopeful-wizardly-archimedes/mnt/outputs/politiek_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Database en JSON export succesvol!")
print(f"Partijen: {len(data['partijen'])}")
print(f"Verkiezingen: {len(data['verkiezingen'])}")
print(f"Zetels records: {len(data['zetels'])}")
print(f"Kabinetten: {len(data['kabinetten'])}")
print(f"Beloftes: {len(data['beloftes'])}")
print(f"Stemgedrag: {len(data['stemgedrag'])}")
print(f"Financiën: {len(data['financien'])}")
print(f"Aanwezigheid: {len(data['aanwezigheid'])}")
