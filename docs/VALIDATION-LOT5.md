# Validation du lot 5 — UBS et stabilisation BNP

16 septembre 2026, Windows / Python 3.14.3. Suite du [lot campus/BNP](VALIDATION-LOT4.md).

## Résultat

- **UBS étudiants/graduates : 17 offres importées** depuis le portail public, parmi un tableau annoncé de 165 annonces.
- Pagination complète du tableau, puis filtre local Trading/Markets et descriptions détaillées : **23 requêtes**, **45 secondes**.
- Premier import UBS silencieux : 17 nouvelles, aucune modification, fermeture ou alerte.
- Base et CSV : **491 offres enregistrées**, dont **83 avec un score ≥ 70** après correction des exclusions de stages.
- **Neuf sources activées pour huit employeurs** : Jane Street, Deutsche Bank, Morgan Stanley, Citi, Barclays, Goldman Sachs (deux sources), BNP Paribas et UBS.

La première tentative UBS a rejeté les liens localisés contenant `frmSiteId`. Ce paramètre a été vérifié dans les réponses publiques, ajouté à la validation stricte et couvert par un test ; cette tentative n'avait importé aucune donnée partielle.

## Stabilisation BNP

Le connecteur réunit désormais les alias strictement identiques d'un identifiant employeur avant import, en choisissant une URL stable. Des contenus métier différents sous un même identifiant font échouer la source. Trois tests couvrent les ordres d'apparition et les conflits.

Relecture réelle du 16 septembre : **23 offres distinctes reçues**, 64 requêtes, 128 secondes, **0 nouvelle**, 2 mises à jour, **0 fermeture**, **0 alerte**. Le périmètre retourné diffère de celui du 15 septembre ; les offres absentes ne sont pas fermées car cette recherche est partielle. Les 491 offres stockées ne constituent donc pas un inventaire garanti de 491 postes encore ouverts.

## Vérifications

- **196 tests réussis**, couverture globale **91 %**.
- Ruff lint et format validés ; Mypy sans erreur sur 20 modules.
- UBS : contexte anonyme, pagination, taille par défaut de 50 quand `PageSize=0`, détails, exigences conservées, URLs localisées, identités, erreurs et absence de données de session dans les payloads métier.
- BNP : filtrage de recherche conservé entre pages, descriptions JobPosting, alias et conflits testés.
- Dates UBS : `lastupdated` non utilisé comme publication. Les deadlines sans heure/fuseau restent non interprétées.
- Scans et vérifications n'envoient aucune candidature. Telegram est désactivé ; aucun watcher laissé actif.

## Société Générale : prochaine intégration

La page officielle de recherche est accessible. Son moteur Quantum utilise un échange OAuth ; il n'a pas été appelé. Le répertoire public lié en pied de page redirige vers `/fr/Technical/toutes-les-offres`, vérifié accessible le 16 septembre. Ce chemin fournit une piste de collecte publique directe. La lecture des détails, la couverture anglaise, la gestion des langues et les tests restent à réaliser : la source demeure désactivée.

JPMorgan reste désactivé après son refus HTTP 403 précédent. Le portail UBS professionnel n'est pas couvert par le connecteur étudiants/graduates. Docker, CI hébergée et exploitation prolongée sur VPS restent à vérifier.

## Reproduire

```powershell
.\.venv\Scripts\python.exe -m trading_radar scan --source ubs
.\.venv\Scripts\python.exe -m trading_radar scan --source bnp_paribas
.\.venv\Scripts\python.exe -m trading_radar doctor
.\.venv\Scripts\python.exe -m trading_radar list --min-score 70
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
```
