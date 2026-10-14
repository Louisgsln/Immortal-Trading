# Validation — lot 164

Application : e05b83865f8652f03f51fafa353e2a4c0fc43eff. Image : immortal-trading:lot164-source-expansion-20261014.

Six ajouts : State Street, Mizuho, Northern Trust, LSEG, GSA Capital et Quadrature Capital. [Inventaire et limites](RADAR-SOURCES-LOT164.md).

- 258 tests ciblés réussis : profils, off-cycle, API Workday, identités Greenhouse, champs des fiches, localisations HSBC et souhaits ; Ruff et Mypy (126 modules) réussis.
- [CI du correctif](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38556765707) : six contrôles réussis ; 5 424 tests par version Python 3.11–3.14, 34 tests JavaScript et récupération isolée du conteneur réussis.
- Image construite et contrat des assets vérifié : 89 contrôles, 7 modules, empreintes CSS/JavaScript valides.
- Deux lectures publiques stables des six sources. Revalidation supplémentaire avant import.
- Simulation sur copie : 67 fiches retenues, premier import puis zéro création/actualisation au second passage ; zéro alerte créée, zéro appel Telegram ; anciens identifiants, candidatures et journaux d'alertes conservés, souhaits inchangés.
- Sauvegarde version 2 et restauration vers des chemins neufs vérifiées sur la copie ; schéma 4 conservé.
- Le contrôle de fraîcheur a interrompu une première tentative devenue ancienne ; code et configuration ont été rétablis, sans restauration de la base active. Une nouvelle lecture et une sauvegarde sont requises pour la relance.

Installé et vérifié sur OVH le 14 octobre : 67 nouvelles fiches, zéro actualisation historique et zéro alerte à l’import. Les 15 contrôles de préservation passent : base/inode/schéma, identifiants, candidatures, alertes envoyées, journaux, souhaits, digest, curseur et liaisons Telegram. Cinq services Docker en fonctionnement, radar et Dashboard sains, quatre services système actifs et activés au démarrage. Même lien HTTPS privé et garde-fous 404/405/403 ; API souhaits et candidatures validées sans mutation. /statuts indique 97 sources / 85 employeurs, dont 89 sources à jour au relevé ; les huit incidents restent explicites dans l’inventaire. Off-cycle/long 2027, tous scores et horaires 09:00/13:00/18:00 Paris conservés. Le chargement de 1 683 fiches a pris 26,632 secondes ; performance suivie au lot 159.

[Preuves](DELIVERY-LOT164.json) · [Carnet](TASK-BOARD.md).
