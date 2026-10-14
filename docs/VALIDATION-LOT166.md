# Validation — lot 166

Développement : deux collecteurs officiels spécifiques (Scotiabank et D. E. Shaw), quatre profils Workday vérifiés, branche `release/lot166-sources`, commit `d74e0a9cf950548346093feafff7925610625564`.

217 tests ciblés passent, dont 42 nouveaux cas : intégrité du catalogue, identités et URLs, pagination, première page relue, changement liste/fiche, descriptions et exigences manquantes, postes cachés et exploratoires, date rendue non utilisée, routes des filiales publiées, stages off-cycle admis et Summer exclus. Ruff et formatage passent ; Mypy valide les 128 modules. Les 34 tests JavaScript passent.

Image construite : `immortal-trading:lot166-source-expansion-20261014`. Utilisateur 10001, contrat des assets vérifié dans l'image : 89 contrôles et sept modules. Empreinte du collecteur installé dans l'image identique au code et au contexte de déploiement. Aucun secret ou donnée de production dans le contexte public.

Trois lectures complètes concordent sur les six sources. Simulation sur copie : 41 créations au premier passage, aucune au second, aucune actualisation ni alerte ; 7 fiches à score ≥ 70 et 31 à zéro. Anciens identifiants, candidatures, journaux d’alertes et liste de souhaits conservés. Sauvegarde et restauration isolée version 2 vérifiées. Les 5 466 tests Python locaux passent ; 5 466 tests passent sur chacune des versions Python 3.11, 3.12, 3.13 et 3.14 dans la CI. Installation et contrôle final de production réussis : 103 sources / 91 employeurs, 91 à jour au relevé, six ajouts à jour. Les 15 vérifications de préservation passent, base en schéma 4, souhaits en schéma 1 et curseur Telegram conservés. Cinq conteneurs actifs, radar et Dashboard sains ; quatre services système actifs et activés. Même lien privé HTTPS, API souhaits/candidatures, session, origine et CSRF vérifiés. `/statuts` correspond aux 103 lignes de l’inventaire et au Dashboard. Flux tous scores, digest 09:00 Paris et points d’état 13:00/18:00 conservés. Blocage RDC de sudo rétabli et liste originale vérifiée. Aucun message de test envoyé.

Le démarrage initial du Dashboard a dépassé les 120 secondes du déploiement ; code/configuration rétablis sans restauration de la base après l’import silencieux de 41 fiches. Relance : nouvelle sauvegarde vérifiée, zéro création/actualisation/alerte, Dashboard démarré avant les collectes et attente bornée à 300 secondes. Démarrage confirmé, sans erreur ni OOM. Le délai HTTP mesuré reste de 39,64 secondes pour 1 729 fiches ; le lot de performance 159 reste ouvert.

Les six contrôles CI sont verts sur le correctif d74e0a9 : Python 3.11–3.14, JavaScript, construction et récupération isolée du conteneur. [Exécution CI](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38586189270).

[Preuves structurées](DELIVERY-LOT166.json).

[Sources](RADAR-SOURCES-LOT166.md) · [Carnet](TASK-BOARD.md).
