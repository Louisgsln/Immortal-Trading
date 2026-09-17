# Exploitation Docker et contrôles de reprise

## État de validation

Le lot 20 prépare le build verrouillé, un contrôle de santé local et un exercice automatique sur un volume Docker isolé. **Docker Desktop 4.91.0 est installé depuis le 17 septembre 2026**, avec Docker CLI 29.8.0 et Compose 5.5.1. WSL reste à installer : la confirmation administrateur Windows n’a pas pu être validée en l’absence de l’utilisateur. Aucun build ni démarrage de conteneur n’a encore été exécuté. Voir [WINDOWS-DOCKER-SETUP.md](WINDOWS-DOCKER-SETUP.md) pour reprendre l’installation et [VALIDATION-LOT20.md](VALIDATION-LOT20.md) pour les contrôles applicatifs précédents. La présence des contrôles en CI ne vaut pas résultat d’exécution.

## Image et dépendances

Le Dockerfile utilise deux étapes. La première installe le projet avec `uv sync --locked --no-dev --no-editable`. La seconde récupère uniquement l'environnement installé, la configuration, la fixture synthétique et le script de validation. Les dépendances de développement et les connecteurs optionnels ne sont pas installés dans l'image standard.

Les images Python 3.12 slim Bookworm et uv 0.11.8 sont fixées par leurs empreintes de registre. Leurs manifestes ont été consultés le 17 septembre 2026. `uv.lock` fixe les dépendances applicatives ; [DEPENDENCIES.md](DEPENDENCIES.md) décrit aussi le backend de construction et les limites de ce verrouillage. Une mise à jour des images ou paquets doit être explicite, suivie des tests et de l'exercice de reprise.

Le processus s'exécute sous UID/GID **10001**. Compose monte la configuration en lecture seule et la base dans `radar-data`, garde la racine du conteneur en lecture seule et fournit `/tmp` en mémoire. Les journaux Docker sont limités à trois fichiers de 10 Mo. Les secrets `.env` et les bases locales sont exclus du contexte de build.

Références : [intégration uv/Docker](https://docs.astral.sh/uv/guides/integration/docker/) et [HEALTHCHECK Docker](https://docs.docker.com/reference/dockerfile/#healthcheck).

## Vérifier avant de démarrer le watcher

Sur une machine disposant de Docker Engine et Docker Compose, depuis le dépôt :

```bash
# Si .env n'existe pas encore, créer sa configuration à partir de .env.example.
# Garder ALERTS_ENABLED=false pour le premier contrôle.
docker compose config --quiet
docker compose build
docker compose run --rm radar doctor
```

`doctor` prépare la base si elle n'existe pas. Contrôler le résultat et les sources configurées. Un volume neuf reprend la propriété du répertoire de données de l'image ; un volume déjà présent doit autoriser l'UID 10001 à écrire. Ne pas résoudre un problème de droits en supprimant le volume.

L'exercice CI construit l'image puis exécute `scripts/smoke_container.py` avec un volume neuf, utilisateur non-root, réseau coupé et les restrictions du service. Il effectue deux scans synthétiques, contrôle la déduplication et le CSV, crée des historiques synthétiques, sauvegarde, vérifie, restaure et compare les onze tables. Le volume dédié est supprimé en fin de job ; aucun volume de production n'est utilisé.

Pour valider uniquement le parcours Python sans Docker, avec l'environnement installé :

```powershell
python scripts/smoke_container.py --local --data-dir data
```

Ce mode conserve ses preuves dans un nouveau répertoire `data/container-smoke-*`. Son rapport porte explicitement `local_workflow_only` : il ne valide ni le build, ni Linux, ni les droits d'un volume Docker.

## Démarrer et surveiller

Avant une actualisation, `trading-radar scan --dry-run --source flow_traders`
permet d'[examiner les changements](SCAN-PREVIEW.md) sans modifier la base active.
Le scénario de reprise inclut désormais deux aperçus synthétiques : sur une base
absente, puis après création des candidatures et alertes de test. Il vérifie
l'absence de création initiale et la préservation des onze tables et du CSV.

```bash
docker compose up -d
docker compose ps
docker compose logs --tail 100 radar
docker compose exec radar trading-radar health
```

Le démarrage lance le watcher et ses collectes publiques. Les notifications dépendent de la configuration explicite. Un seul watcher doit écrire dans une base donnée.

Pour archiver ponctuellement l'état courant : `docker compose exec radar trading-radar monitor record`. Les commandes `monitor history` et `monitor show IDENTIFIANT` lisent ensuite les rapports du volume, sous `data/health-history`. Cette commande n'installe aucune planification. Ces fichiers sont à conserver séparément des sauvegardes SQLite ; voir [MONITORING.md](MONITORING.md).

La commande [health](HEALTH.md) lit la base sans la créer ni la migrer. Elle vérifie notamment l'intégrité, le schéma et la fraîcheur des collectes. Le Dockerfile l'exécute toutes les cinq minutes, avec un délai maximum de trente secondes, une période initiale de dix minutes et trois échecs avant l'état unhealthy. Une source jamais collectée ou trop ancienne rend le contrôle critique. Un nouveau déploiement peut donc être unhealthy tant que ses sources n'ont pas été initialisées avec succès.

Ce contrôle ne prouve pas que le watcher tourne actuellement : les données peuvent rester fraîches pendant le seuil de 24 heures après son arrêt. Docker signale l'état unhealthy ; la politique `restart: unless-stopped` ne redémarre pas à elle seule un processus encore vivant sur ce seul signal. Examiner les logs et le JSON de santé avant intervention. Les alertes incertaines et les échecs récents encore couverts par une collecte fraîche apparaissent comme avertissements.

## Sauvegarder le volume

```bash
# Choisir un nouveau nom à chaque sauvegarde.
docker compose exec radar trading-radar backup create data/backups/radar-2026-09-17.zip
docker compose exec radar trading-radar backup verify data/backups/radar-2026-09-17.zip
docker compose cp radar:/app/data/backups/radar-2026-09-17.zip ./radar-2026-09-17.zip
```

La sauvegarde tient compte du WAL pendant le fonctionnement du watcher. Conserver une copie vérifiée sur un stockage distinct et protégé ; l'archive restée dans le même volume ne suffit pas. Les archives contiennent les notes et historiques personnels et ne sont pas chiffrées. La configuration et les secrets se conservent séparément.

Pour examiner la conservation locale : `docker compose exec radar trading-radar backup plan data/backups --json`.
Ce [plan](BACKUP-RETENTION.md) vérifie les archives et explique celles retenues par
la politique choisie ; il ne supprime rien et ne remplace pas la copie sur un
stockage distinct. Cette commande Docker reste à valider sur un hôte équipé.

## Restaurer puis reprendre

1. Arrêter les écritures avec `docker compose stop radar`.
2. Garder la base existante. Restaurer une archive présente dans le volume vers un nouveau chemin, par exemple `docker compose run --rm radar backup restore data/backups/radar-2026-09-17.zip data/recovered/jobs.db`.
3. Remplacer explicitement `DATABASE_URL` dans la section `environment` de Compose par `sqlite:////app/data/recovered/jobs.db`. Cette valeur Compose prime sur celle de `.env`. Garder les alertes et rappels désactivés pendant le contrôle.
4. Exécuter `doctor`, `stats`, `applications list` et `alerts list --all` avec `docker compose run --rm radar ...`. Revoir les messages éventuellement livrés après le snapshot : leur état sauvegardé peut être antérieur à la livraison.
5. Quand le contenu attendu est confirmé, recréer le service avec `docker compose up -d` et vérifier les logs ainsi que `health`. La réactivation des alertes reste une décision distincte.

Le [guide de sauvegarde](BACKUPS.md) précise les refus d'écrasement et les limites de restauration. `docker compose down` conserve les volumes nommés ; **ne pas ajouter `-v`** pour un service dont les données doivent être gardées.

## Travaux restant à valider

Exécution effective du job Docker sur Linux, exercice de reprise sur l'hôte cible, surveillance prolongée et copie distante des sauvegardes. Aucun VPS n'a été provisionné et aucun service distant n'a été lancé par le lot 20.
