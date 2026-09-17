# Lot 36 — Installation propre et validation Docker en CI

Travaux du **17 septembre 2026** avec deux sous-agents : correction des imports
pytest et revue indépendante du Dockerfile, du scénario de reprise et du workflow.
L’agent principal a intégré la CI, exécuté la suite locale et suivi les runs GitHub.

## Défaut reproduit et correction

Le [premier run](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35202317678)
du commit `27bc2b4` échouait à la collecte des tests : `pytest` ne trouvait pas
`scripts.measure_workday_cache` et `scripts.probe_workday_queries`. Les validations
locales précédentes utilisaient `python -m pytest`, qui ajoutait la racine aux imports.

`pythonpath = ["."]` dans la configuration pytest rend les deux commandes cohérentes.
Les utilitaires restent hors du paquet de production. Aucun contournement par
suppression de tests ou modification des règles métier n’a été introduit.

## CI et preuves

- Installation depuis le lock avec `--no-editable` sur Python 3.11, 3.12, 3.13 et 3.14.
- Matrice sans annulation automatique des autres versions au premier échec.
- Rapports JUnit conservés 14 jours.
- Build Docker suivi d’un appel réel de l’ENTRYPOINT `trading-radar --help`.
- Exercice synthétique sur volume neuf : réseau coupé, racine en lecture seule,
  capacités retirées, absence de nouveaux privilèges et utilisateur non-root.
- Rapport JSON, stderr, journal de build et journaux des commandes synthétiques
  récupérés avant suppression du conteneur et du volume dédiés.
- Artefacts limités aux preuves synthétiques, conservés 14 jours. Les pipelines Bash
  conservent le code d’échec de Docker même avec `tee`.

Le [run de validation](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35203330404)
porte sur le commit `28bda22` : **les cinq jobs ont réussi**.

| Environnement | Résultat | Couverture |
| --- | --- | --- |
| Ubuntu, Python 3.11 | 2 068 tests, 120,23 s | 96 % |
| Ubuntu, Python 3.12 | 2 068 tests, 119,15 s | 96 % |
| Ubuntu, Python 3.13 | 2 068 tests, 101,67 s | 96 % |
| Ubuntu, Python 3.14 | 2 068 tests, 181,47 s | 96 % |
| Docker Linux, Python 3.12 | Build, ENTRYPOINT et reprise réussis | Sans mesure de couverture |

Le rapport Docker confirme `mode=container`, `uid=10001`, huit offres synthétiques,
deux scans sans duplication, deux aperçus sans écriture, export dashboard de huit
offres, statistiques de deux scans et une sauvegarde valide conservée par le plan
de rétention. La restauration et sa réouverture préservent **les onze tables**,
y compris les candidatures et alertes synthétiques avec leurs historiques.

Les quatre rapports JUnit et l’[artefact Docker](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35203330404/artifacts/10488713129)
ont été publiés, avec expiration au **1er octobre 2026**. Le conteneur et son volume
synthétiques ont ensuite été supprimés avec succès. Les logs des cinq jobs et le
rapport JSON Docker extrait sont également conservés localement dans le dossier du lot.

## Contrôles locaux

- **2 068 tests réussis**, couverture **96 %**, installation non éditable Windows.
- Collecte réussie par console, module et environnement installé ; 82 tests des
  utilitaires concernés également exécutés séparément.
- Ruff : **159 fichiers** ; mypy : **64 fichiers** ; diff Git sans erreur d’espacement.
- Contenu des **11 tables SQLite** et **CSV inchangés** : 814 offres, 812 actives,
  163 prioritaires et 250 pertinentes conservées.
- Aucune modification de collecteur, score, candidature, alerte ou donnée métier.

Les preuves locales sont dans `data/discovery/lot36/` : erreur CI initiale,
rapport de tests Windows et comparaison des données. Les artefacts de CI complètent
ces preuves pour Linux et Docker.

## Limite du poste Windows

Docker Desktop est installé, mais WSL attend toujours une installation administrateur
sur le poste de l’utilisateur. Une validation GitHub ne remplace pas le contrôle
du poste Windows ou d’un futur VPS. Voir [WINDOWS-DOCKER-SETUP.md](WINDOWS-DOCKER-SETUP.md).
