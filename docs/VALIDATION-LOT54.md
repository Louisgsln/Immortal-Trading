# Lot 54 — Reprise de la collecte Société Générale

## Cause vérifiée sur les pages publiques

Le carnet signalait `SG visible reference mismatch`. L'audit borné des deux
annuaires FR/EN sélectionne 31 fiches. La première, [Assistant Algo Trader,
26000K6O](https://careers.societegenerale.com/offres-d-emploi/assistant-algo-trader-26000K6O-fr),
reproduit l'échec : les lignes de référence et de dates utilisent désormais un
élément `span` contenant le libellé dans un autre `span`, suivi de la valeur texte.
Le lecteur ne reconnaissait que l'ancien conteneur `div`.

Le correctif accepte ces deux structures auditées. Il conserve la valeur texte
directe, le rejet des libellés dupliqués, l'égalité entre référence visible et
annuaire, ainsi que les contrôles de référence JSON-LD, d'URL canonique et de dates.
Les sections de missions/profil restent obligatoires. Aucun repli vers la seule
référence structurée, aucune requête authentifiée et aucun changement de budget.

## Audit et répétition

Les 31 fiches publiques sélectionnées sont lues avec succès, en respectant le
client HTTP existant et les règles robots. Les pages capturées sont ensuite
rejouées sans réseau sur une sauvegarde SQLite créée, vérifiée et restaurée.

- Base initiale : **783 offres** ; après répétition : **784**.
- **31 fiches reçues**, **une ajoutée**, zéro mise à jour métier, zéro clôture.
- Nouvelle référence `26000K0O`, Investment Banking Analyst – Y1 – Loan Capital
  Markets and Syndication – Project Finance : score nul, exclue de la cible.
- Scores existants et offres des autres sources inchangés.
- Candidatures existantes, historique de candidatures, alertes et historique
  d'alertes préservés. Aucun envoi pendant la répétition.
- Deuxième passage : zéro ajout, zéro mise à jour. Les observations source sont
  normalement actualisées ; les offres absentes ne sont pas clôturées.

## Vérifications

**3 069 tests Windows réussis, quatre ignorés** (liens symboliques indisponibles).
Les 43 tests Société Générale couvrent les deux langues et les deux structures,
les dates explicites ou textuelles, références contradictoires, doublons entre
structures, valeurs absentes ou ambiguës et désaccords de dates. Ruff, formatage
et mypy réussis. L'ancien format reste accepté sans différence de métadonnées.

La livraison et les contrôles GitHub sont consignés après vérification effective.
