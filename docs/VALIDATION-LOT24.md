# Validation du lot 24 — Tendances historiques

Validation locale du 17 septembre 2026, sous Windows et Python 3.14.3.
Trois sous-agents ont livré les calculs, la commande et l'interface ; l'agent principal
a réalisé l'intégration, la revue et les vérifications sur la base réelle.

## Fonctionnalités livrées

- `trading-radar trends --days 30` : rapport JSON de 1 à 365 jours calendaires UTC.
- Onglet **Tendances** : périodes 7/30/90 jours, quatre indicateurs, graphique des
  premières détections et tableau quotidien de sept compteurs.
- Lecture cohérente des trois tables utiles, sans migration ni création de base.
  Limites de lecture explicites ; refus des données incohérentes sans résultat partiel.
- Une erreur de tendances reste localisée : les offres peuvent toujours être consultées.
- Exercice de reprise synthétique enrichi : huit premières détections et deux scans
  vérifiés avec la nouvelle commande.

## Observation réelle et préservation

Les trois fenêtres contiennent toute l'activité actuellement conservée, du 14 au
17 septembre. Sur 30 jours, les totaux sont :

| Compteur | Total |
| --- | ---: |
| Premières détections locales | 813 |
| Mises à jour de fiches | 12 |
| Recalculs de score | 109 |
| Fermetures enregistrées | 2 |
| Réouvertures enregistrées | 0 |
| Scans enregistrés | 45 |
| Occurrences de sources en échec | 5 |

Les empreintes et nombres de lignes des **11 tables** sont identiques avant et après
le rapport et l'export HTML. Les 813 offres, dont 811 actives, et le suivi existant
sont conservés. Le HTML a été régénéré et le serveur local actualisé.

Les premiers imports expliquent l'essentiel des détections : ces volumes ne mesurent
pas les publications du marché. Les scans incluent les imports/rejeux locaux, même
sans requête réseau. Une source en échec sur plusieurs scans compte plusieurs fois.
Le dernier jour UTC est partiel ; le rapport ne reconstitue pas un stock quotidien
d'offres actives. Les tendances et les offres sont des observations distinctes.

## Vérifications

- **1 362 tests réussis**, soit 102 supplémentaires ; couverture Python **96 %**.
- 78 tests de calculs, limites, erreurs, fuseaux, WAL, concurrence et lecture seule ;
  21 tests CLI ; trois tests d'intégration au dashboard.
- Ruff : **124 fichiers** conformes ; mypy : **53 fichiers**, sans erreur.
- Paquet reconstruit hors réseau depuis `uv.lock`, installé sans mode éditable et testé.
- Navigateur : compteurs et journal vérifiés, changements de période 7/30/90,
  rendu bureau et largeur mobile 390 px sans débordement horizontal de la page.

Preuves locales sous `data/discovery/lot24/` : `trends.json`, `cli-trends.json`,
`preservation.json`, `test-results.xml` et `test-results.txt`. Ces fichiers de travail
sont ignorés par Git. Le guide utilisateur est [TRENDS.md](TRENDS.md).

Aucune nouvelle dépendance, migration ou modification des références `sources/`.
Aucune collecte réseau, notification ou automatisation lancée dans ce lot.
Le scénario synthétique a été testé localement ; Docker et l'hébergement distant
restent à valider sur un hôte équipé.
