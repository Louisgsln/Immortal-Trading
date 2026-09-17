# Validation du lot 2 — Banques Workday

15 septembre 2026, Windows / Python 3.14.3. Suite du [premier lot](VALIDATION.md).

## Vérifications locales

- **102 tests réussis** : scoring, CLI, stockage, adaptateurs et transport HTTP.
- Ruff lint et format : réussis sur `src`, `tests` et `scripts`.
- Mypy : aucune erreur sur 15 modules.
- Configuration et base vérifiées avec `doctor`.
- `pip check` : aucune dépendance cassée.

Le nouveau corpus Workday teste les corps POST de recherche, la pagination réelle (total seulement sur la première page pour certains tenants), les limites, les pages courtes/répétées, les refus d'accès et de détails, les chemins invalides et la déduplication entre requêtes. Il vérifie aussi les lieux multiples et la séparation entre publication et début de contrat.

Les règles de score ont reçu des tests pour Summer Analyst, les stages, l'apprentissage, les VIE et les années de début contradictoires. `rescore` est vérifié pour préserver les observations et ne pas générer d'alertes.

## Scans réels

| Source | Résultats de recherche `trading` | Offres retenues et détaillées | Requêtes | Durée approximative |
|---|---:|---:|---:|---:|
| Deutsche Bank | 296 | 22 | 38 | 75 s |
| Morgan Stanley | 326 | 17 | 35 | 69 s |
| Citi | 1 224 | 54 | 117 | 234 s |
| Barclays | 118 | 20 | 27 | 53 s |

Les trois premières banques ont été collectées avec une concurrence limitée, en environ 234 secondes au total ; Barclays a été validée séparément. Les 217 requêtes comptent les politiques robots, les pages de recherche et les détails. Les limites de périmètre sont décrites dans [SOURCES.md](SOURCES.md).

Résultats d'import :

- **113 offres bancaires ajoutées**, portant la base à **343 offres** avec les 230 Jane Street déjà présentes.
- Premier passage réussi de chaque banque silencieux : **aucune notification envoyée**.
- Deuxième passage Deutsche Bank : 22 offres reçues, **0 nouvelle**, **0 modification**, **0 fermeture**, **0 alerte**.
- Recalcul hors réseau avec `rescore` : 20 enregistrements actualisés après modification des règles ; **38 offres au total** ont ensuite un score d'au moins 70. Ce score reste un classement automatique, à examiner humainement.
- CSV actualisé dans `data/jobs.csv`. Bases et réponses de découverte restent ignorées par Git.

Un premier essai avait volontairement rejeté les pages Workday dont le total passait à zéro. L'examen des réponses publiques a établi que ce comportement est normal sur les pages suivantes pour trois tenants. La correction et son test sont maintenant intégrés ; ces tentatives échouées n'ont pas importé de données partielles.

## État opérationnel et limites

- Cinq sources activées dans la configuration : Jane Street et les quatre banques ci-dessus.
- Pas de processus de surveillance laissé en arrière-plan ; lancement via `trading-radar watch`.
- Telegram reste désactivé et aucun envoi réel n'a été effectué.
- Workday est une couverture ciblée, pas un inventaire exhaustif : recherche `trading`, filtrage des titres, détail de tous les résultats retenus. Pas de fermeture automatique à partir de cette recherche partielle.
- La cadence de cinq minutes est comptée après la fin d'un scan. Pour Citi, la durée observée ajoute presque quatre minutes : optimisation de la fraîcheur encore nécessaire.
- Des lieux exprimés comme noms d'immeubles ou adresses sans ville peuvent rester non normalisés ; le titre et le texte d'origine sont conservés.
- Goldman Sachs et JPMorgan sont repérés mais pas encore connectés. SuccessFactors, Oracle et les autres portails bancaires restent à intégrer selon la feuille de route.
- Les dates de fin de publication Workday ne sont pas converties en deadlines candidat sans validation de leur signification.
- Docker, la CI hébergée et un fonctionnement prolongé sur VPS restent non vérifiés, comme au premier lot.

## Reproduire

```powershell
.\.venv\Scripts\python.exe -m trading_radar scan --source workday
.\.venv\Scripts\python.exe -m trading_radar rescore
.\.venv\Scripts\python.exe -m trading_radar list --min-score 85
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m mypy src/trading_radar
```
