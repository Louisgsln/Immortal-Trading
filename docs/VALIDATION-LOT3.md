# Validation du lot 3 — Goldman Sachs / Oracle

15 septembre 2026, Windows / Python 3.14.3. Suite du [lot Workday](VALIDATION-PHASE2.md).

## Résultat

- **Goldman Sachs activé et importé : 70 offres**, avec descriptions complètes.
- Base principale : **413 offres**, dont **58 avec un score d'au moins 70**. Le score reste un classement automatique à vérifier.
- JPMorgan : **désactivé après HTTP 403** depuis cet environnement. Connecteur Oracle testé hors réseau uniquement, sans prétendre couvrir ses offres en production.
- Six sources configurées et validées en réseau au fil des lots : Jane Street, Deutsche Bank, Morgan Stanley, Citi, Barclays et Goldman Sachs.

## Contrôles locaux

- **140 tests réussis**, couverture globale **90 %** ; connecteurs Goldman et Oracle à 98 % chacun.
- Ruff lint et format réussis sur `src`, `tests` et `scripts`.
- Mypy : aucune erreur sur 18 modules source.
- `doctor` : configuration et SQLite valides ; sources désactivées et leurs motifs visibles.
- `pip check` : aucune dépendance cassée.

Les nouveaux tests vérifient les corps de recherche, pages et totaux, identifiants stables, erreurs GraphQL avec HTTP 200, limites, fiches incomplètes ou discordantes, refus 403 sans reprise, lieux multiples, absence de dates inventées et réunion des descriptions/responsabilités/qualifications Oracle. Les tests Workday existants restent valides après mutualisation des options de recherche.

## Validation réseau Goldman

La recherche anonyme du portail a annoncé 350 résultats pour `trading` lors de la découverte. Le tri `RELEVANCE` répétait une même offre entre deux pages. Le premier scan a donc échoué avant import. Le tri public `POSTED_DATE DESC`, également proposé par le portail, a permis une pagination réussie ; les contrôles de total et de doublons restent actifs.

Import complet du périmètre retenu :

| Mesure | Résultat |
|---|---:|
| Offres importées après filtrage | 70 |
| Requêtes, robots inclus | 90 |
| Durée | 178 secondes |
| Nouvelles offres | 70 |
| Modifications / fermetures | 0 / 0 |
| Alertes | 0 — démarrage silencieux |

Une seconde vérification a relu **trois fiches réelles** puis exécuté le pipeline sur une **copie SQLite** de la base : 3 reçues, 0 nouvelle, 0 modification, 0 fermeture, 0 alerte, dates de première observation conservées. Cette vérification limitée valide la relecture et la déduplication ; ce n'est pas un deuxième scan de toutes les pages. La base principale et ses observations sont restées celles de l'import complet.

La copie de vérification est dans `data/validation/`, ignoré par Git. Le CSV principal est `data/jobs.csv`.

## Limites et exploitation

- Goldman couvre les catégories professional/early career recherchées avec `trading` et filtrées par titre ; les programmes campus restent à ajouter.
- Les avis réglementaires « Notice of Filing » sont ignorés. Les fiches explicitement inactives sont écartées.
- Recherches partielles : aucune fermeture automatique déduite d'une absence. Pas de date de publication Goldman inventée.
- Avec 178 secondes de collecte et cinq minutes entre scans, la cadence observée serait proche de huit minutes sur ce périmètre ; la configuration ne garantit pas une détection en cinq minutes.
- JPMorgan demande encore une validation réseau réussie, notamment du schéma de ses détails, avant activation. Aucun contournement du refus d'accès n'a été tenté.
- Telegram reste désactivé ; aucun watcher laissé en arrière-plan.
- Docker, CI hébergée et exploitation prolongée sur VPS restent non vérifiés.

## Reproduire

```powershell
.\.venv\Scripts\python.exe -m trading_radar scan --source goldman
.\.venv\Scripts\python.exe scripts/verify_goldman_repeat.py
.\.venv\Scripts\python.exe -m trading_radar doctor
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
```

La vérification de relecture utilise un échantillon de trois offres déjà stockées et une copie de base ; une offre modifiée entre-temps entraîne un résultat à examiner plutôt qu'un succès artificiel.
