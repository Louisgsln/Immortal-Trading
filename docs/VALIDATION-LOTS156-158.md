# Validation — lots 156–158

Livrés sur `vps-b7a073e2.vps.ovh.net` le 12 octobre 2026. Application `89fd622`, passerelle `2527898`, image `immortal-trading:lot156-all-offers-wishlist-20261012`.

## Résultat

Chaque nouvelle offre collectée et vérifiée est envoyée automatiquement dans Telegram, même à 0. Le score reste affiché ; les imports initiaux, archives, offres expirées/inactives et références en conflit ne sont pas relancés. Les critères de priorité continuent de s'appliquer aux rappels et actualisations. Le périmètre de collecte reste défini par les portails, leurs recherches et leurs filtres. `/offres` et `/souhaits` affichent cinq fiches par page.

Le bouton « Ajouter à la liste des souhaits » est signé et lié au bot et au destinataire privé. Il n'envoie pas de candidature et ne change pas son statut. La vue mobile affiche directement les favoris, avec tri et filtres repliables. Retirer un favori conserve l'offre et la candidature ; « J'ai postulé » conserve les notes, prochaines actions et étapes ultérieures. Le suivi existant permet de modifier les notes et échéances. La page ouverte relit candidatures et favoris toutes les dix secondes.

Les nouvelles routes de la passerelle privée sont validées ; le même lien HTTPS sans identifiant ni mot de passe fonctionne. Le certificat est accepté, les cookies gardent Secure/HttpOnly/SameSite et les contrôles de session, origine et CSRF restent appliqués. Racine publique et fichiers privés : 404 ; POST de la page : 405 ; API sans CSRF : 403. Des POST volontairement invalides sur wishlist et Applied donnent 400 sans modifier de données.

## Sources

91 sources pour 79 employeurs et 90 URL distinctes, 85 à jour au relevé du 12/10 à 16:45 UTC. [Liste complète](RADAR-SOURCES-LOTS156-158.md).

| Nouvelle source | Fiches initiales | Deux lectures stables |
|---|---:|---|
| BP | 6 | Oui |
| Shell | 3 | Oui |
| Marex | 7 | Oui, couverture partielle |
| Wellington Management | 3 | Oui |
| AllianceBernstein | 1 | Oui |
| Arrowstreet Capital | 1 | Oui |

21 fiches importées sans alerte rétroactive après revalidation des snapshots publics. Les cinq autres recherches sont complètes dans leur périmètre filtré ; Marex ne fournit pas d'inventaire exhaustif. Une absence de fiche n'y déclenche pas de fermeture. Nomura campus reste en attente ; BNP général/campus, Jefferies campus, Bank of America et TD apparaissent dans les incidents datés. Le worker reste actif malgré ces incidents.

## Vérifications et préservation

- CI application : [38273180835](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38273180835), six contrôles réussis ; 5 354 tests par version Python 3.11–3.14, 34 tests JavaScript et récupération isolée du conteneur.
- Passerelle : 13 tests ciblés réussis, configuration Caddy validée puis contrôles HTTPS réels ; [CI complémentaire](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38280220695) en cours au relevé.
- Chromium, largeur 390 px : ajout au favori, offre à 0 visible, mise à jour simulée depuis Telegram reçue, tri, filtres repliables, Postulé conservant le favori, retrait conservant la candidature, retour aux offres ; aucune erreur JavaScript. Tests sur base synthétique.
- Image installée : contrat du document validé, 89 contrôles, hashes CSS/JavaScript vérifiés ; Dashboard sans identifiants Telegram et sans envoi d'alertes.
- Copie de la base de production : deux scans des six portails, 21 fiches au premier puis zéro au second ; zéro appel réseau Telegram ; nouvelles offres à 0 envoyées une seule fois avec transport simulé ; favori partagé, retrait, Postulé et sauvegarde/restauration vérifiés.
- Production : sauvegarde vérifiée avant déploiement ; inode et schéma 4 de la base, anciens IDs, candidatures, historiques, alertes envoyées, liaison Telegram, curseur monotone et réglage du digest conservés.
- Favoris : base annexe `jobs.db.wishlist.sqlite3` privée mode 0600 ; archive version 2 vérifiée avec les deux bases et empreintes ; anciennes archives version 1 restent vérifiables et restaurables. Aucune restauration sur la base active.
- Cinq services Docker en fonctionnement, radar et Dashboard sains, quatre services système actifs et activés au démarrage. Horaires conservés : 09:00, 13:00 et 18:00 Europe/Paris.
- Une carte réelle à 0 avec bouton des souhaits a été envoyée une fois ; accusé de réception Telegram confirmé. Aucun ancien historique d'alerte ni curseur n'a été réinitialisé.

Le chargement HTTPS observé de 1 581 fiches prend 18,6 secondes ; son optimisation est inscrite au prochain lot.

[Preuves JSON](DELIVERY-LOTS156-158.json) · [Carnet des tâches](TASK-BOARD.md).
