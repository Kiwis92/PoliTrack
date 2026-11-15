# Conceptbeloften (wachten op goedkeuring)

Bestanden in deze map worden door de pijplijn **niet** verwerkt. Zo kan de redactie de specificatie (doel, richting, kernelementen, horizon, zoektermen, dossiers) vastleggen vóórdat iemand de stemmingen ziet, zoals het selectieprotocol eist.

Goedkeuren = het bestand verplaatsen naar `beloften/` en `"status": "concept"` veranderen in `"status": "vastgesteld"`. Vanaf dat moment is de specificatie bevroren; latere wijzigingen horen in een changelog in het bestand.

Bij elke belofte staat `formatie_uitkomst` nog op `null`. Die vult de redactie in na lezing van het coalitieakkoord.
