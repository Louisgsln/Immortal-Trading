# State Street — lot 180 installé

Installé le 19 octobre 2026 à 19:21 UTC, commit 9041be5d1c40a7ebb45ce9d6e7c5cefa3862cb20. Workday publie des lignes ne contenant que bulletFields et une référence de forme R- suivie de six chiffres. Cette forme exacte est désormais reconnue uniquement pour State Street, avec les mêmes limites, contrôles de pagination et signalements que les autres références opaques auditées.

La vérification réelle récupère **40 offres complètes** et conserve deux lacunes visibles : **R-794329** et **R-796523**. Aucun titre, lieu ou lien n’est fabriqué pour ces références. La source reste affichée **partielle**, et aucune fermeture ne découle de ces lacunes.

L’essai sur une nouvelle sauvegarde restaurée, puis l’import réel, ajoutent une fiche, ne ferment aucune offre et préservent le suivi, les souhaits et les historiques. Les quinze contrôles de conservation passent. Seuls les trois services cloud sont remplacés par l’image du lot 180 ; Dashboard et passerelle HTTPS restent en place.

**92 tests ciblés passent**, dont neuf nouveaux cas : maintien des autres offres, aucun accès à une fiche inventée, forme exacte, rejet des champs supplémentaires, mauvais formats et absence d’assouplissement des autres sources. Ruff, format et Mypy sur 133 modules passent. Le contrat de 89 contrôles passe dans la nouvelle image. La [CI du correctif](https://github.com/Louisgsln/Immortal-Trading/actions/runs/39309313310) réussit **5 752 tests Python 3.14** et les 34 tests JavaScript ; les trois autres versions et le job Docker hébergé sont encore en cours au dernier relevé. La CI complète des lots 177–179 est entièrement verte.

Au 19/10/2026 à 19:23 UTC : **128 sources / 116 employeurs**, **121 à jour**, radar et Dashboard sains. Les incidents restants sont dans l’[inventaire daté](RADAR-INVENTORY-20261019.json) et le [carnet](TASK-BOARD.md). Sudo est de nouveau bloqué avec la liste originale complète. [Preuves](DELIVERY-LOT180.json).
