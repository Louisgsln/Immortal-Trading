# Validation du lot 4 — Campus Goldman et BNP Paribas

Imports du 15 septembre 2026 ; stabilisation des alias BNP le 16 septembre. Windows / Python 3.14.3.

## Imports réels

| Source | Fiches reçues | Nouvelles offres distinctes | Requêtes | Durée |
|---|---:|---:|---:|---:|
| Goldman campus | 30 | 30 | 38 | 73 s |
| BNP Paribas | 33 | 31 | 81 | 162 s |

Chaque premier passage a été silencieux : aucune alerte envoyée et aucune fermeture. Les recherches campus `trading` et `ficc` ont été dédupliquées avant lecture des fiches. La recherche BNP annonçait 462 résultats, parcourus par pages de dix, puis filtrés par titre.

Les deux fiches BNP supplémentaires sont des alias : mêmes identifiants, titres, descriptions, lieux, dates de publication et contrats, mais URLs avec ou sans suffixe `-1`. Le premier import les a fusionnées en deux mises à jour. Le connecteur choisit désormais une URL stable avant import ; un identifiant réutilisé avec un contenu différent fait échouer la source plutôt que d'écraser silencieusement une offre. Tests couvrant les deux ordres d'apparition des alias.

Après ces imports : **474 offres** dans la base. Recalcul du score après ajout des exclusions `OffCycle` et `Stage` : deux offres campus corrigées, **74 offres avec un score ≥ 70**. Ces chiffres constituent le bilan du lot 4 ; les sources ajoutées ensuite les font évoluer.

## Vérifications

- 173 tests réussis avant stabilisation des alias ; 176 après ajout des trois tests d'alias/conflit BNP.
- Couverture mesurée avant ces trois tests : 91 % globale, 97 % pour BNP.
- Ruff et Mypy validés.
- Dates campus de planification non copiées en dates de début d'emploi.
- BNP : mot-clé et numéro de page contrôlés, liens strictement limités au domaine officiel, description complète et publication issues de `JobPosting`.
- Le filtre `--source` accepte maintenant une clé de configuration, en plus du type de connecteur.
- Toutes ces recherches restent partielles : aucune fermeture déduite d'une absence.

Le tableau de découverte UBS/Société Générale figure dans SOURCES.md. Leur accessibilité initiale ne valait pas encore validation des connecteurs. Telegram reste désactivé et aucun watcher n'est lancé en arrière-plan.
