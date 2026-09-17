# Dépendances verrouillées

Le fichier `uv.lock` est généré par **uv 0.11.8** depuis PyPI. Il fixe les versions,
les marqueurs Python/plateforme et les empreintes SHA-256 des distributions des
dépendances d'exécution et des extras `dev`, `jobspy` et `ats`. Les plages du
`pyproject.toml` restent les contraintes de compatibilité ; une installation
avec `pip install .` ne reproduit pas ce verrouillage.

## Installer et vérifier

Depuis la racine du projet, avec uv 0.11.8 et Python installé :

```sh
uv lock --check
uv sync --locked --no-dev --no-editable
uv run --no-sync trading-radar --help
```

`--locked` refuse un lock absent ou devenu incohérent avec les dépendances du
projet. `--frozen` ne vérifie pas cette cohérence et n'est pas utilisé dans le
parcours de validation. Après une installation contrôlée, `--no-sync` évite une
nouvelle synchronisation lors de l'exécution.

Pour développer et exécuter les contrôles :

```sh
uv sync --locked --extra dev
uv run --no-sync pytest
uv run --no-sync ruff check src tests scripts
uv run --no-sync ruff format --check src tests scripts
uv run --no-sync mypy src
```

La CI installe avec `--no-editable` pour tester le paquet construit. Pytest ajoute
explicitement la racine du dépôt à son chemin d’import : les utilitaires de
`scripts/` restent ainsi testables avec `pytest` comme avec `python -m pytest`,
sans être ajoutés au paquet de production. Les quatre versions Python de la
matrice sont exécutées même si l’une échoue. Les rapports JUnit et les preuves
du scénario Docker synthétique sont conservés comme artefacts pendant 14 jours.

`dev` est ici un **extra**, pas un groupe de dépendances : il faut le demander
avec `--extra dev`. Les extras tiers restent facultatifs :

```sh
uv sync --locked --extra jobspy
uv sync --locked --extra ats
```

Une synchronisation est exacte : les extras non demandés peuvent être retirés
de l'environnement ciblé. Pour réunir plusieurs extras, les demander dans la
même commande. Ces installations facultatives ne sont pas nécessaires aux
collecteurs natifs.

## Outils de construction

Hatchling est fixé à `1.32.0` dans `[build-system]`. Les contraintes
`[tool.uv].build-constraint-dependencies` figent aussi ses dépendances actuelles :
packaging `26.3`, pathspec `1.1.1`, pluggy `1.6.0`, tomlkit `0.15.1` et
trove-classifiers `2026.6.1.19`. Elles s'appliquent à la construction isolée
effectuée par uv, sans ajouter ces paquets au service en production.
Voir la [documentation officielle des contraintes de build](https://docs.astral.sh/uv/reference/settings/#build-constraint-dependencies).

Limite : les dépendances de cette construction isolée sont contraintes par
version, mais leurs empreintes ne sont pas couvertes par `uv.lock` si elles
n'appartiennent pas aussi au graphe applicatif. Les constructions depuis les
sources de paquets facultatifs peuvent avoir d'autres dépendances de build.
Le verrouillage ne constitue pas une garantie d'image Docker identique octet
pour octet, ni un audit de vulnérabilités.

## Mise à jour volontaire

```sh
uv lock --upgrade-package httpx
uv lock --check
uv sync --locked --extra dev
uv run --no-sync pytest
uv run --no-sync ruff check src tests scripts
uv run --no-sync ruff format --check src tests scripts
uv run --no-sync mypy src
```

Relire les changements de `uv.lock`, puis les conserver avec le code. Une mise
à jour de Hatchling implique aussi de vérifier ses dépendances et d'actualiser
les contraintes de build. Garder la même version d'uv en local, CI et Docker
pour reproduire le parcours testé.

## Validation du lot 20

Le 17 septembre 2026, sous Windows et CPython **3.14.3** :

- résolution réelle de **53 entrées de paquets**, incluant les extras, avec
  `requires-python = ">=3.11"` conservé et des marqueurs propres aux versions ;
- environnement distinct `data/validation-lot20-venv` créé avec le lock,
  l'extra `dev` et une installation non éditable : **900 tests réussis** ;
- Ruff **0.16.8** : analyse et format valides ; mypy **1.20.2** : aucun problème ;
- reconstruction hors réseau du projet après ajout des contraintes de build ;
- environnement distinct `data/validation-lot20-core-venv`, sans extra, créé
  depuis le cache avec `--locked --offline --no-dev --no-editable` :
  **24 paquets installés**, commande `trading-radar --help` fonctionnelle ;
- seconde installation du noyau dans `data/validation-lot20-core312-venv`, avec
  CPython **3.12.13** déjà présent sur la machine : **24 paquets installés**,
  commande `trading-radar --help` fonctionnelle ;
- `uv lock --check --offline` réussi après les modifications finales.

Versions directes installées : httpx **0.28.1**, pydantic **2.13.5**,
PyYAML **6.0.3**, python-dotenv **1.2.3**, typer **0.27.2**, filelock **3.32.7**
et protego **0.6.2**. Les environnements et le cache de validation sont sous
`data/`, ignorés par Git ; l'environnement `.venv` existant n'a pas été modifié.

Les 900 tests correspondent au code initial du lot 20 avant l'ajout de la
commande de santé. Consulter le rapport du lot pour le total final.

Le lock résout Python 3.11 et les extras facultatifs ; cette vérification locale
n'établit pas à elle seule que chaque combinaison Python/OS/extra s'installe et
s'exécute correctement. Consulter le rapport du lot pour la validation Docker
et les contrôles CI réellement exécutés.
