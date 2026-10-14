# Validation — lot 169

Code : `b9e60c6799d4c096f78f5add76a743d0ded31219`, branche `release/lot169-quant-funds`. Collecteur CFM, trois identités Greenhouse et profils VPS ; QRT élargi sans modifier le profil historique général.

77 nouveaux cas de test et 103 tests ciblés passent : pagination CFM, changement liste/fiche, canonique, total, doublons, limites, catalogue vide explicite, descriptions complètes et rubriques en gras, faits cachés ignorés, identités globales/ANZ, métadonnées nulles distinctes des champs absents, stages quantitatifs QRT auparavant rejetés, Summer/support exclus. Ruff, formatage et Mypy passent, 129 modules. Les 34 tests JavaScript passent.

Image `immortal-trading:lot169-quant-funds-20261014` construite depuis un contexte public isolé. Sept fichiers vérifiés par SHA-256 ; profil VPS `b50f2d409854b960c49d400f64a668c41f6bf173ea38756299e455c18176c260`. Contrat des assets : 89 contrôles, sept modules, utilisateur 10001. Aucun secret ni fichier d'exploitation dans ce contexte.

Deux lectures complètes concordantes des cinq périmètres : QRT 54/198, CFM 9/24, Xantium 6/8, BlueCrest 1/8, Dymon 4/12. Simulation dans un conteneur sans réseau, sur copie SQLite : 51 créations au premier passage, zéro au second ; aucune actualisation, fermeture ni alerte, zéro appel Telegram. Anciens identifiants, candidatures, journaux d'alertes et souhaits conservés. Sauvegarde/restauration isolée version 2 vérifiée ; base schéma 4. Dashboard de simulation : 1 786 fiches et contrat complet valide.

Les **5 543 tests Python locaux passent**, sans échec ni test ignoré, en 811,64 secondes. Les **5 543 tests réussissent sur chacune des versions Python 3.11, 3.12, 3.13 et 3.14** dans la CI du correctif `b9e60c6`. Les six contrôles sont verts : quatre versions Python, 34 tests JavaScript, construction du conteneur et récupération isolée sans réseau. Les assets du Dashboard et les sauvegardes/restaurations sont également vérifiés dans l'image de CI. Aucune relance de test nécessaire.

Installation et contrôle final de production réussis le 14 octobre à 18:42 UTC : **107 sources / 95 employeurs**, **97 à jour**, cinq périmètres de ce lot à jour. **51 créations**, zéro actualisation, fermeture et alerte à l'import. Les 15 vérifications de préservation passent : base et souhaits, anciens identifiants, candidatures et historiques, alertes envoyées, curseur/binding/digest/heartbeat Telegram, sauvegarde version 2 vérifiée. Base schéma 4, souhaits schéma 1. Aucune restauration de la base active.

Cinq conteneurs actifs avec redémarrage automatique, radar et Dashboard sains ; quatre services système actifs et activés. Nouveau Dashboard démarré avant les workers, attente de démarrage bornée à 300 secondes ; aucune reprise par rollback nécessaire. Même lien privé HTTPS sans connexion, session et CSP, origine/CSRF et API souhaits/candidatures vérifiés. Les sondes POST invalides sont rejetées sans modifier le suivi. Contrat réel : 89 contrôles sur 1 787 fiches. Temps HTTP au relevé : 28,214 secondes ; performance 159 toujours ouverte.

`/statuts` reconnu par le parseur du bot, inventaire 107/95 concordant avec le Dashboard ; `/sources` paginé dans la limite Telegram. Flux des nouvelles offres tous scores conservé, digest 09:00 Paris et points d'état 13:00/18:00 inchangés. Dashboard sans secrets Telegram et sans émission de notifications. Aucun message de test envoyé. Dix incidents de portails conservés, Nomura campus toujours en attente humaine ; aucun accès contourné. Blocage de sudo rétabli : liste originale de 33 commandes RDC vérifiée à l'identique.

[Preuves structurées](DELIVERY-LOT169.json).

[CI](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38614555234) · [Sources et périmètre](RADAR-SOURCES-LOT169.md) · [Carnet](TASK-BOARD.md).
