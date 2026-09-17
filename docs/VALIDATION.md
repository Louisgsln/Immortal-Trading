# Validation du premier lot

Ce rapport conserve les résultats historiques du premier lot. Voir [la validation du lot 2](VALIDATION-PHASE2.md) pour la couverture Workday et les résultats actuels.

Date locale : 15 septembre 2026 (Europe/Paris). Environnement : Windows, Python 3.14.3, environnement virtuel local `.venv`.

## Résultats

| Vérification | Résultat |
|---|---|
| Tests pytest | **76 réussis** |
| Couverture des lignes | **88 %** |
| Ruff lint | Réussi |
| Ruff format | Tous les fichiers formatés |
| Mypy | Réussi, 14 modules sans erreur |
| `pip check` | Aucune dépendance cassée |
| CLI `doctor` | Configuration et SQLite valides |
| Dépendances optionnelles | ats-scrapers 0.3.0 et python-jobspy 1.1.82 installés ; imports et signatures vérifiés |
| Copie du master prompt | SHA-256 identique au fichier fourni |

Les tests couvrent les huit exemples de référence, exclusions et exigences d'expérience, normalisation, URLs et empreintes, séparation d'IDs homonymes, déduplication inter-sources, transactions, fermetures et réouvertures, bootstrap par source, échecs indépendants, snapshots incomplets, envois Telegram simulés, alertes incertaines, deadlines déjà passées, CSV, CLI et adaptateurs optionnels simulés.

## Dry run

Sur les huit offres synthétiques :

- Premier scan : 8 nouvelles offres, 5 pertinentes, 0 alerte.
- Second scan : 0 nouvelle offre, 0 doublon, 0 alerte.
- Base `data/demo.db` et export `data/demo.csv`, séparés des offres réelles.

## Vérification réseau réelle

Le flux public Greenhouse de Jane Street a été lu avec le client du projet, après lecture de `robots.txt` :

- `doctor --network` : 230 offres reçues.
- Premier scan : 230 nouvelles offres enregistrées, 2 requêtes HTTP, environ 3,2 secondes, démarrage silencieux.
- Second scan : 230 offres reçues, **0 nouvelle offre**, **0 fermeture**, **0 alerte**.
- Le second passage a mis à jour 57 enregistrements après amélioration des règles de score. Ces changements incluent les explications du score ; ils ne constituent pas 57 nouvelles offres.
- Après correction : 16 offres ont un score d'au moins 55, dont 2 d'au moins 70. Ces scores ne constituent pas une validation manuelle de leur adéquation.
- Données réelles : `data/jobs.db`, `data/jobs.csv`, ignorées par Git.

La revue manuelle de résultats a permis d'ajouter des tests pour « 3+ years of analyst experience », « 5+ years of analyst experience » et les offres recherchant explicitement un profil expérimenté.

## Limites de validation et de couverture fonctionnelle

- Seule Jane Street a fait l'objet d'une collecte réseau de bout en bout. Lever et Ashby sont testés sur fixtures, sans employeur activé.
- Les adaptateurs JobSpy et ats-scrapers sont installés et testés par contrat, mais leurs collectes réseau n'ont pas été exécutées. Le transport de ces bibliothèques ne passe pas par le client HTTP partagé.
- ats-scrapers est intégré via son dataset public. Ses scrapers directs et les ATS bancaires Workday/SuccessFactors restent à réaliser.
- Aucun message Telegram réel n'a été envoyé ; aucun token ou identifiant de chat n'a été fourni. Les tests simulent les réponses de Telegram.
- Docker n'est pas disponible dans le PATH de ce poste : Dockerfile et Compose sont livrés, sans build ni exécution vérifiés.
- Le workflow GitHub Actions est fourni, mais n'a pas été lancé sur GitHub. Aucun dépôt distant n'est configuré et aucun push n'a été effectué.
- Le watcher n'a pas été laissé en arrière-plan. Le suivi prolongé, les sauvegardes et la reprise sur un VPS restent à éprouver.
- Pas de dashboard, d'édition de candidatures, de rappels périodiques de deadline, de recherche floue automatique ni de backend PostgreSQL dans ce lot.
- Les catégories et dates reposent sur des règles simples : des offres ambiguës, des dates implicites et des exigences formulées différemment peuvent nécessiter des corrections. Les offres dont la deadline structurée est déjà dépassée sont conservées mais ne génèrent pas d'alerte.
- Les sources de recherche partielle ne ferment pas les offres sur simple disparition. Une offre vue par un agrégateur peut rester active jusqu'à une confirmation de clôture ; cette politique prudente évite les fausses fermetures.

## Reproduire

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar --cov-report=term-missing
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
.\.venv\Scripts\python.exe -m mypy src/trading_radar
.\.venv\Scripts\python.exe -m trading_radar doctor
.\.venv\Scripts\python.exe -m trading_radar scan --demo
```

Le nombre d'offres des sites réels peut évoluer. Les tests hors réseau restent indépendants de ces variations.
