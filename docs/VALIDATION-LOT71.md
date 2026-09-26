# Lot 71 — Fiabilité des collectes et nouvel ordre de développement

## Mesure avant modification

Le 26 septembre 2026, analyse en lecture seule des huit dernières heures :
114 cycles enregistrés et 1 184 tentatives de source. Le cycle médian durait
239 secondes, le plus long 320 secondes. Les intervalles médians entre succès
atteignaient 485 secondes pour Macquarie et 658 secondes pour Citi, malgré
un intervalle configuré de cinq minutes après chaque tentative.

Le journal des scans recensait cinq échecs de pagination UBS (quatre sur le
portail professionnel, un sur le campus), deux Optiver et deux refus CAPTCHA
Nomura campus. Le journal de service contient une troisième erreur Nomura
absente des cycles enregistrés. Les refus restent visibles.

## Changements

- Planification indépendante par source, priorité à la plus en retard, limite
  globale de concurrence et absence de double collecte d'une même source.
- Sessions anonymes séparées ; espacement des requêtes partagé par site et
  politiques d'accès renouvelées à chaque tentative.
- Limite de durée commune de 600 secondes, temporisation après échec également
  avant le premier succès, intervalles longs configurés jamais raccourcis.
- Une seule reprise complète des listes UBS/Optiver qui changent pendant la
  pagination, dans le budget initial. Première page relue avant les détails.
  Aucun mélange des listes, reprise de CAPTCHA ou import partiel trompeur.
- Verrou de collecte séparé du verrou d'écriture ; édition du suivi possible
  pendant les requêtes employeur et scans concurrents refusés.
- Alertes différées lors d'un échec de leur source, livraison limitée aux sources
  sélectionnées, signal d'activité fondé sur la tentative active la plus ancienne.
- Retrait de l'enrichissement IA et de la comparaison avec le CV ; extension
  des employeurs ajoutée au [plan confirmé](DEVELOPMENT-PLAN.md).

## Audit réel et simulation

- UBS campus : 15 offres et 22 requêtes ; UBS professionnels : 33 offres et
  47 requêtes ; Optiver : 27 offres et 40 requêtes.
- Une première observation a été rejetée pour pagination changeante, sans import.
  Les catalogues UBS vérifiés séparément contenaient 154 et 532 annonces avant
  filtrage des titres ; la première page de chacun est restée stable à la relecture.
- La sauvegarde active a été vérifiée et restaurée vers une copie distincte.
  Deux scans des 75 offres : aucun ajout, mise à jour, clôture ou alerte.
- Les six tables candidatures, historique des candidatures, alertes, historique
  des alertes, versions et scores restent strictement identiques. 787 offres conservées.

## Vérifications

- Suite complète Windows : 3 668 tests réussis et quatre ignorés ; cinq tests
  ajoutés ensuite sur les verrous, l'espacement partagé, la livraison ciblée et
  le signal d'activité sont également réussis.
- Scénarios de source lente, renouvellement indépendant d'une source rapide,
  annulation, priorité aux sources en attente, sessions isolées, suivi éditable,
  collecte exclusive, durée maximale et reprise après échec vérifiés.
- Scénarios UBS/Optiver : reprise réussie, deuxième échec bloquant, contrôle de
  la première page, refus des doublons d'une seule page et CAPTCHA sans reprise.
- Ruff, formatage et vérification des types réussis.

## Livraison

Publication, sauvegarde de déploiement, contrôles GitHub et observation active
à consigner après installation. Les comptes de scans du watcher correspondent
désormais à des tentatives individuelles : voir [le guide](SOURCE-RELIABILITY.md).

## Suite

Compléter les fiches BNP/UBS/Barclays, puis le ciblage et la couverture des
recherches. L'extension des employeurs suit le nouvel ordre demandé ; aucun
travail d'enrichissement IA ou de comparaison avec un CV n'est prévu.
