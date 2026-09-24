# Lot 51 — Provenance Nomura

## Périmètre

Suite de l'audit du [lot 41](NOMURA-EXPERIENCE-PROVENANCE-LOT41.md) : attacher
l'extrait exact du champ **Position Specifications → Experience** aux minima
déjà reconnus, avec une origine `description`. Le tableau doit être unique,
commencer par Corporate Title et terminer le champ Experience par Qualification.
Les autres formulations ne reçoivent aucune provenance de tableau inventée.

Le lecteur numérique écarte notamment préférences de durée, négations,
alternatives au diplôme et bornes inversées. Dans les libellés audités,
`preferably in Securitisation Market` qualifie le domaine, pas la durée.
Les grades restent une information séparée et ne fournissent aucune durée.

## Mesure sur les données actuelles

Une sauvegarde SQLite cohérente des **773 offres** du 25 septembre 2026 a été
créée, vérifiée puis restaurée vers une nouvelle base locale. Sur les **16 offres
Nomura**, les minima reconstruits restent identiques. Le corpus a changé depuis
le lot 41 : six tableaux audités sont présents et un septième minimum se trouve
hors tableau (Equity Sales Trader, quatre ans).

| Référence | Minimum | Score conservé |
| --- | ---: | ---: |
| 1283059800 | 2 | 74 |
| 1339221200 | 3 | 54 |
| 1373072800 | 1 | 92 |
| 1405548900 | 0 | 74 |
| 1372610900 | 3 | 54 |
| 1397978500 | 2 | 53 |

Seul `experience_evidence` change sur ces six fiches. Les 767 autres restent
identiques, ainsi que les huit tables hors offres/versions/historique de scores :
schéma, observations source, entreprises, scans, alertes, historique d'alertes,
candidatures et historique de candidatures. Le deuxième passage est sans effet.
La mise à jour hors ligne ne prétend pas avoir relu les pages employeur et ne
change aucune date d'observation. Le collecteur produira les mêmes preuves aux
prochaines collectes.

## Vérifications

- Suite complète Windows : 2 978 tests réussis et quatre ignorés (liens
  symboliques indisponibles). Après durcissement des frontières du tableau,
  138 tests ciblés réussis, incluant trois nouveaux contre-exemples.
- Ruff, formatage et mypy réussis ; paquet installable construit.
- Tests de valeurs réelles et contre-exemples : préférences de durée ou de domaine,
  alternatives, négations, fourchettes inversées, tableau absent/dupliqué/cité,
  contraintes de provenance, grades indépendants et conservation du minimum zéro.
- Retour compatible des anciens payloads ; propagation collecteur → modèle →
  dashboard ; ajout sur copie sans autre modification et contrôle d'idempotence.
- Les preuves sont affichées comme texte dans les fiches du dashboard.
  Vérification navigateur sur la base restaurée : **Trading Support**, minimum
  d'un an et score 92 conservés, extrait `Experience 1-3 years` visible sous
  **Description employeur · Position Specifications → Experience**.

Cette reconnaissance est bornée aux formulations auditées. Un minimum non reconnu
ne signifie pas zéro année d'expérience et le score ne garantit pas l'éligibilité.
