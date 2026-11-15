# Resultaten

Per belofte één bestand `resultaten/<belofte-id>.json` met het geaccordeerde resultaatoordeel. Het wordt gevuld via het beoordelingsscherm (`beoordelen/`).

```json
{
 "oordeel": "gerealiseerd | deels_gerealiseerd | niet_gerealiseerd | loopt_nog | niet_toetsbaar",
 "vlaggen": ["externe_omstandigheid", "zonder_steun_partij", "in_gang"],
 "toelichting": "...",
 "bronnen": ["https://..."],
 "wederhoor": true,
 "door": "github-naam",
 "op": "2026-11-15T12:00:00Z"
}
```

Een oordeel "niet_gerealiseerd" geldt pas als geaccordeerd wanneer `wederhoor` op `true` staat.
