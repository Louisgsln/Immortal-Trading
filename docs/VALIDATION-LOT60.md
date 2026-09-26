# Lot 60 — Contrôles de santé depuis le dashboard

## Comportement livré

La vue Santé du serveur modifiable permet d'enregistrer explicitement l'état
actuel dans l'historique local, puis affiche l'évolution entre les deux derniers
contrôles. L'export et l'aperçu ordinaire restent en lecture seule. Le tableau des
sources conserve sa date de chargement ; l'action actualise seulement l'historique.

Les comparaisons distinguent amélioration, dégradation, diagnostic modifié et
source ajoutée ou retirée. Une base indisponible ou des seuils de fraîcheur
différents sont signalés. La collecte partielle, les conflits et les restrictions
d'accès, introduits au lot 56, sont désormais acceptés par les archives de santé.
Leur rang d'avertissement est identique à celui d'un échec récent ; les anciens
rapports conservent leur format et les états inconnus sont toujours rejetés.

Le point d'entrée local exige la session, une origine identique et un corps JSON
vide. Aucun chemin, seuil ou réglage n'est accepté depuis le navigateur. Les
contrôles n'écrivent pas dans SQLite, ne déclenchent pas de collecte et n'envoient
aucun message. Un clic en cours désactive le bouton ; aucune relance automatique
n'est faite après une réponse incertaine. Si le contrôle est conservé mais qu'un
ancien rapport est illisible, la réussite et l'indisponibilité de l'historique
sont toutes deux indiquées, sans inviter à répéter l'écriture.

## Vérifications

- 36 nouveaux tests : diagnostics issus de collectes simulées réelles, archives
  et retours à la normale, changement entre avertissements, état inconnu rejeté,
  enregistrement protégé, méthodes et corps refusés, erreurs sans données privées,
  archive antérieure illisible et base métier absente après démarrage du serveur.
- Suite complète Windows : 3 268 tests réussis, quatre ignorés. Ruff, formatage
  et vérification des types réussis.
- Sauvegarde vérifiée et restaurée : 787 offres, 11 tables strictement inchangées
  après deux contrôles par l'API locale ; archives relues et comparées.
- Navigateur sur cette copie : enregistrement confirmé, historique actualisé,
  comparaison d'un diagnostic partiel synthétique puis d'un contrôle réel sain,
  rendu visuel vérifié ; bouton caché dans l'export, aucune erreur JavaScript.
- L'audit local observe 24 sources à jour. Ce constat ne garantit pas la
  disponibilité ultérieure des portails employeur.

## Livraison

Publication, installation après sauvegarde et contrôles GitHub à consigner
après leur exécution.

## Suite du carnet

Poursuivre l'audit des rubriques employeur et la surveillance prolongée des
sources. L'historique reste alimenté explicitement ; aucune tâche de capture
automatique n'est ajoutée. La copie distante des sauvegardes attend une destination.
