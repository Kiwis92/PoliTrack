# Beoordelingen

Per belofte een map `beoordelingen/<belofte-id>/` met:

- `codering-<naam>.json`: de onafhankelijke codering van één codeur. `<naam>` is `ai` of een GitHub-gebruikersnaam.
- `beslissingen.json`: de eindbeslissing voor stemmingen waar de codeurs verschillen.

Deze bestanden worden gevuld via het beoordelingsscherm (`beoordelen/`) en door de AI-codeur in de geplande taak. Een stemming telt pas mee in de score als twee codeurs haar onafhankelijk hebben gecodeerd.

Formaat van een codering:

```json
{
 "codeur": "naam",
 "coderingen": {
  "<besluit-id>:<zaak-id>": {
   "opname": true,
   "richting_voorstem": "voor_belofte",
   "directheid": 1,
   "onderzoeksmotie": false,
   "coalitiediscipline": false,
   "toelichting": "..."
  },
  "<ander-besluit-id>:<zaak-id>": {
   "opname": false,
   "reden_code": "U3",
   "toelichting": "..."
  }
 }
}
```

Reden-codes: U1 procedureel · U2 vervangen door gewijzigde versie · U3 richting niet codeerbaar · U4 belofte is bijzaak in een pakket.
