# Lot 103 — Déploiement cloud sous budget zéro

Préparé le **6 octobre 2026** pour la demande d'exploitation continue hors du PC.
Budget confirmé : gratuit uniquement. Aucun compte, abonnement ou serveur n'est
créé, et aucune identité d'hébergeur n'est disponible dans cette session.

`compose.cloud.yaml` définit le scanner et les sauvegardes, avec un écouteur
Telegram optionnel. Les services utilisent un tag de livraison explicite,
redémarrent après une sortie et partagent le dossier persistant choisi ; un
dossier absent n'est pas créé implicitement par Compose. Aucun port public
n'est exposé. Secrets locaux dans `.env.cloud`, exemple sans identifiant réel.

Le lanceur exige une base compatible existante, sans initialisation ni migration.
Le transfert Windows est décrit dans [CLOUD-FREE.md](CLOUD-FREE.md) : arrêt des
anciens écrivains, sauvegarde cohérente, restauration vers une destination neuve,
revue du suivi et de la file d'alertes. Le démarrage du scanner et de Telegram
exige `RADAR_CUTOVER_CONFIRMED=true` ; ce paramètre ne remplace pas la vérification
réelle des processus de l'ancien PC. Le wrapper est remplacé par le processus
CLI, qui conserve ses verrous habituels.

Le service de sauvegarde crée une archive cohérente vérifiée immédiatement,
puis chaque 24 heures. Un échec est consigné et réessayé après dix minutes,
sans fuite du texte d'exception. Un verrou interdit deux boucles sur le même
état. SIGTERM interrompt l'attente proprement ; aucune suppression automatique
n'est ajoutée. Les limites de stockage et une copie distincte restent à suivre.

Le Dockerfile accepte une autorité de certification de proxy par secret BuildKit
optionnel, sans désactiver TLS ni conserver cette autorité dans l'image. Les
fichiers de runtime appartiennent à l'UID 10001 : un checkout avec permissions
600 reste lisible par l'utilisateur non-root dans l'image. Le bind de config
sur un serveur doit aussi permettre la lecture par cet UID.

## Vérifications

- **88 tests ciblés réussis**, dont 12 tests du déploiement : base absente sans
  création, schéma incompatible sans migration, coupure explicite, validation
  locale des identifiants, sauvegarde/restauration du suivi, reprise après erreur
  et santé nécessitant un heartbeat et des collectes fraîches.
- Ruff et formatage réussis sur **282 fichiers** ; mypy sur **101 modules**.
- Configuration Compose complète et YAML cloud-init validés.
- Manifestes épinglés Python et uv lus au registre : plateformes Linux amd64 et
  arm64 présentes. Le parcours exécuté ici est amd64 ; l'exécution sur une VM
  ARM reste à vérifier sur cet hôte.
- Image Docker construite avec le lock, la CA montée par secret et UID 10001 :
  `sha256:88d5574a1a9499a363640116b553e3d317f4ae7dfd384dadd5cd972bbf61b42e`.
- Parcours Docker réel **sans réseau**, racine en lecture seule, capacités
  retirées et `no-new-privileges` : huit offres synthétiques, deux scans sans
  doublon, sauvegarde/restauration de **11 tables identiques**.
- Lanceur exécuté dans cette image : preflight sur base existante, refus du
  watcher avant confirmation de migration, archive de huit offres vérifiée,
  première sauvegarde de la boucle, refus de sa seconde instance, arrêt
  SIGTERM avec code zéro et données conservées après recréation du conteneur.

Le preflight de l'exercice conserve `source_health: critical` : les sources de
production n'y sont pas collectées et aucun heartbeat de scanner réel n'est
inventé. Les conteneurs et volumes synthétiques sont supprimés après vérification.

Les CI des lots **99, 100, 101 et 102** sont désormais toutes réussies ; le lot
102 inclut les quatre versions Python et le parcours Docker :
[run 37389509439](https://github.com/Louisgsln/Immortal-Trading/actions/runs/37389509439).
La CI du présent lot sera vérifiée séparément après publication.

## Mise en service encore bloquée

La session dispose d'un moteur Docker de développement ; cela ne constitue pas
une VM de production permanente. Son réseau restreint ne donne accès ni aux
sites employeur ni à Telegram et aucune VM n'est joignable par SSH. Le compte
d'hébergement gratuit, l'hôte accessible et la configuration de production
doivent être fournis pour terminer. L'offre gratuite proposée est documentée
avec ses limites de capacité et de reprise des machines inactives ; aucun
fonctionnement continu garanti ni collecte réelle n'est revendiqué.
