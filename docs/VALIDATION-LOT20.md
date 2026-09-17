# Validation du lot 20 — Dépendances, santé et préparation Docker

17 septembre 2026. Trois sous-agents ont travaillé en parallèle sur le verrouillage des dépendances, le scénario de reprise et la CI, ainsi que le contrôle de santé. L'agent principal a intégré les changements, préparé l'image et Compose, puis effectué les vérifications finales. Une revue croisée a corrigé les exemples `docker compose exec`, qui doivent appeler explicitement `trading-radar`.

## Résultat et limite principale

Les dépendances sont verrouillées, la santé est consultable hors réseau et le parcours synthétique de reprise fonctionne. **Docker, Podman et WSL sont absents de ce poste** : le build de l'image, l'exercice sur volume Linux et le déploiement VPS n'ont pas été exécutés. Le workflow GitHub Actions est préparé pour les effectuer ; aucun résultat de CI distante n'est revendiqué.

Guides : [DEPENDENCIES.md](DEPENDENCIES.md), [HEALTH.md](HEALTH.md), [OPERATIONS.md](OPERATIONS.md).

## Dépendances et installation

- `uv.lock` généré réellement avec uv **0.11.8** depuis PyPI : **53 entrées**, versions, marqueurs de compatibilité et SHA-256 des distributions.
- Python `>=3.11` et extras `dev`, `jobspy`, `ats` conservés. Le noyau installé seul comporte **24 paquets**, sans outils de développement ni connecteurs facultatifs.
- Hatchling **1.32.0** et versions de ses dépendances de construction contraints explicitement ; leurs hashes ne sont pas tous couverts par le lock applicatif.
- Installations isolées du noyau réussies sous Windows **Python 3.12.13** et **3.14.3**. Aucun Python ajouté au système, environnement `.venv` préexistant conservé.
- Environnement de développement reconstruit depuis le lock sous `data/validation-lot20-venv`, installation non éditable. Les fichiers Python installés ont été comparés aux sources finales : identité complète.
- `uv lock --check --offline` réussi. Les extras tiers sont résolus dans le lock, mais pas installés/testés dans toutes les combinaisons Python/OS.

## Santé réelle sans écriture

`trading-radar health` ouvre la base existante en lecture seule et lit ses métriques dans une même transaction. Il contrôle le schéma courant, `quick_check`, les clés étrangères, les derniers succès des sources activées et les alertes unknown/sending. Il n'initialise pas Telegram et n'effectue pas de migration.

Le contrôle réel retourne **healthy**, code **0**, **24 sources fraîches** au seuil de 24 heures et **0 alerte unknown/sending**. Les empreintes et nombres de lignes des **11 tables** sont identiques avant et après. Les 811 offres et leurs historiques sont préservés. Preuves : `data/discovery/lot20/health.json` et `health-preservation.json`.

La santé mesure la disponibilité et l'âge des données, pas la présence instantanée du watcher. Une base neuve ou une source jamais collectée est critique. Un échec récent reste dégradé tant que la dernière réussite est fraîche. Les alertes incertaines donnent un avertissement sans bloquer la disponibilité.

## Exercice synthétique de reprise

Le script `scripts/smoke_container.py` travaille dans un nouveau répertoire et neutralise les variables de base/Telegram héritées. Deux scans de démonstration produisent **8 offres**, sans doublon ni alerte. Le CSV est contrôlé. Une candidature et une alerte incertaine synthétiques remplissent les historiques avant l'archive.

Création, vérification et restauration sont exécutées par les vraies commandes CLI. Les **11 tables** sont identiques après restauration et après ouverture de la copie avec `Repository`. L'historique de candidature contient une ligne et l'historique d'alerte deux lignes ; aucun notifier n'est appelé.

Exécution locale : `data/container-smoke-4luhoo8_/report.json`, avec le marqueur **local_workflow_only**. Le même parcours passe dans les tests de l'installation verrouillée. Cela ne remplace pas la validation Linux/volume Docker.

## Image et CI préparées

- Deux étapes Docker : construction uv verrouillée puis environnement d'exécution non éditable, sans uv ni sources de développement nécessaires au runtime.
- Images Python 3.12 slim Bookworm et uv 0.11.8 fixées par les empreintes obtenues des registres publics. Cette lecture de manifestes ne constitue pas un build.
- UID/GID 10001, volume de données, racine et configuration en lecture seule dans Compose, `/tmp` temporaire, capacités supprimées et logs limités.
- Sonde `health` toutes les cinq minutes, délai maximal de trente secondes, amorçage dix minutes, trois échecs avant unhealthy.
- CI configurée pour Python **3.11–3.14**, `uv sync --locked --extra dev`, tests et analyse, puis build et scénario de restauration sans réseau sur un volume synthétique unique.
- YAML lu avec succès et configuration relue ; la validation native `docker compose config` est incluse dans la CI, pas exécutée sur ce poste.

## Vérification finale

- **954 tests réussis**, soit **54 supplémentaires** ; couverture globale **95 %**.
- Santé : **51 tests**, module couvert à **97 %**, CLI à **100 %**. Schéma incompatible, base absente/corrompue, clés étrangères, dates invalides, seuils, sources désactivées, alertes et erreurs de configuration vérifiés.
- Une écriture WAL concurrente entre deux lectures ne mélange pas les métriques : la transaction de santé conserve un état cohérent, puis le contrôle suivant voit l'écriture.
- Exercice de reprise : **3 tests**, dont refus de l'utilisateur root et préservation des données opérateur synthétiques.
- Ruff **0.16.8** : analyse et format valides sur **100 fichiers** ; mypy **1.20.2** : **43 modules**, aucune erreur.
- Suite finale exécutée sous Python **3.14.3** contre le paquet installé depuis le lock, et non uniquement contre un arbre de sources éditable.

Les preuves et environnements de travail sont sous `data/`, ignorés par Git. Aucun fichier `sources/` modifié, aucune collecte réelle, candidature envoyée, notification ou watcher lancé.

## Suite logique

Exécuter le job Docker sur un hôte équipé, puis valider la reprise et les permissions du volume sur la cible. En parallèle, les prochains travaux applicatifs possibles restent l'audit de couverture des sources et l'historisation des rapports de santé. La copie distante et la politique de conservation des sauvegardes restent à configurer séparément.
