# Lot 58 — Missions et diplômes Jump Trading

## Périmètre audité

Les descriptions conservées de 26 offres Jump Trading ont été inspectées.
Les listes suivant **What You'll Do / What you will do** alimentent les extraits
de missions. Les listes **Skills You'll Need / Skills you will need** alimentent
les diplômes mentionnés. Les variantes d'apostrophe et de casse sont reconnues.

Les autres introductions et rubriques restent hors périmètre. Les listes doivent
suivre immédiatement leur titre. Pour les missions, plusieurs rubriques
concurrentes entraînent le repli vers l'extrait de description habituel.
Les sous-listes restent rattachées à leur phrase introductive : « one or more
projects » n'est pas transformé en une liste de missions toutes obligatoires.

La formulation académique **Master or PhD** est maintenant reconnue comme une
alternative entre les deux niveaux. Elle ne généralise pas le mot « Master »
dans des expressions comme « Master or MS Excel ». Aucun diplôme minimum ni
décision d'éligibilité n'est calculé.

## Impact sur sauvegarde restaurée

- 787 offres, dont 26 Jump Trading.
- 12 nouvelles observations de missions ; 54 anciennes inchangées, soit 66.
- 11 nouvelles observations de diplôme ; 34 anciennes inchangées, soit 45.
- 11 tables identiques après génération du dashboard, dont scores, candidatures,
  historique et alertes. Aucune migration ni reclassification métier.
- Toutes les cartes ont un HTML valide et restent sous la limite Telegram :
  maximum mesuré de 1 170 unités UTF-16 sur ce corpus.

Les prochaines alertes éligibles utilisent les missions reconnues, limitées à
trois extraits de 240 caractères avec ellipse si nécessaire. Le détail du
dashboard conserve les extraits complets et leur provenance. Aucune ancienne
alerte n'est réémise et les messages déjà reçus restent inchangés.

## Validation

- 33 cas ajoutés : rubriques auditées, alternatives, préférences, séparation des
  avantages, contenus cachés, sections ambiguës, listes imbriquées, échappement,
  limites Telegram et conservation des données.
- Navigateur : filtre Jump Trading + Master, neuf résultats ; fiche Python
  Software Engineer avec missions et alternative Bachelor/Master, score 51
  conservé. Aucun message d'erreur JavaScript observé.
- Suite complète Windows : 3 217 tests réussis, quatre ignorés. Ruff et
  vérification des types réussis.
- [CI du lot](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36231945448)
  réussie sur Python 3.11–3.14 et Docker : 3 221 tests Linux, couverture 96 %,
  construction et exercice de restauration du conteneur réussis.

## Installation

- Code `840c27f` publié sur `main`, paquet isolé installé après sauvegarde
  vérifiée le 26 septembre 2026 à 11:10 Paris ; version précédente conservée.
- Les quatre fichiers applicatifs installés correspondent au code publié.
- Dashboard et lecture du suivi répondent correctement : 787 offres, 66 avec
  missions, 45 avec diplômes et six preuves d'expérience Nomura.
- Exclusion de l'offre HSBC Associate seul et conservation des titres mixtes
  vérifiées. Les trois services Windows sont redémarrés ; collectes SIG, HSBC
  et Nomura professionnels réussies après installation.

## Suite du carnet

Poursuivre l'audit des autres rubriques employeur et des rôles hybrides, sans
assimiler une amélioration de présentation à une validation du ciblage métier.
La copie distante de sauvegarde reste conditionnée au choix d'une destination.

Un contrôle du dashboard pendant une collecte a affiché `invalid_timestamp`
pour Nomura professionnels alors que la collecte venait de réussir. La lecture
des offres précède le contrôle de santé, lequel reçoit l'heure de début de
génération : auditer cette concurrence de lecture dans un prochain lot.
Nomura campus, précédemment soumis au CAPTCHA, a une collecte réussie le
26 septembre à 11:01 avec 12 offres ; son accès public peut rester intermittent.
