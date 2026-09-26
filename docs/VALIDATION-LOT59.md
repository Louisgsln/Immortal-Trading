# Lot 59 — Santé cohérente pendant une collecte

## Problème et correction

Au lot 58, Nomura professionnels pouvait apparaître avec une date invalide
alors que sa collecte venait de réussir. La génération du dashboard enregistrait
son heure de départ, lisait les offres puis transmettait cette ancienne heure
au contrôle de santé. Une collecte terminée entre ces étapes semblait future.
Le contrôle autonome pouvait aussi rencontrer une écriture entre son démarrage
et l'ouverture de son instantané SQLite.

En lecture courante, le contrôle conserve son instantané unique et compare
les dates à l'heure de fin de lecture. Le dashboard laisse ce contrôle prendre
sa propre heure. Sa date globale reste celle du début de génération : offres,
santé et tendances sont des observations distinctes, pas une transaction globale.

Les archives reprennent la date du rapport de santé dans leur identifiant et
leur enveloppe, sans modification du format ni réécriture des archives existantes.
Les dates futures réelles et mal formées restent signalées. Une heure passée
explicitement par l'appelant reste un seuil exact, notamment pour les simulations
et autres traitements à heure fixée ; aucune marge de tolérance n'est ajoutée.

## Preuves

- 15 nouveaux tests avec commits SQLite contrôlés avant et après l'ouverture de
  l'instantané, succès, échec, fin de scan, vraie date future, dashboard et archive.
- Sept échecs reproduits avant correction, puis tous ces cas réussis.
- Répétition sur sauvegarde restaurée de 787 offres : Nomura professionnels passe
  de `invalid_timestamp` à `fresh` pour la même collecte intercalée.
- À heure explicite fixe, le contenu du dashboard est strictement identique à
  celui de la version précédente. Les 11 tables restent inchangées, y compris
  scores, candidatures, historiques et alertes.
- L'audit observe 24 sources à jour sur cette copie, sans garantie de disponibilité
  permanente des portails publics.
- Suite complète Windows : 3 232 tests réussis, quatre ignorés. Ruff, vérification
  des types et tests ciblés réussis.
- [CI du lot](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36233005518)
  réussie sur Python 3.11–3.14 et Docker : 3 236 tests Linux, couverture 96 %,
  construction et exercice de restauration du conteneur réussis.

## Livraison

- Code `d8c280a` publié sur `main`, installé après sauvegarde vérifiée le
  26 septembre à 11:31 Paris ; version précédente conservée.
- Les trois fichiers applicatifs installés correspondent au code publié.
- Dashboard et lecture du suivi répondent correctement : 787 offres, 66 extraits
  de missions, 45 mentions de diplôme ; règles Analyst/Associate préservées.
- Vue Santé vérifiée dans le navigateur à 11:32 : 24 sources à jour, aucun
  message d'erreur JavaScript. L'accès des sources peut varier ensuite.
- Scanner, dashboard et Telegram actifs ; collectes DRW, HSBC, Macquarie et
  Crédit Agricole réussies après redémarrage.

## Suite du carnet

Poursuivre l'observation de l'exploitation et l'audit des rubriques employeur.
La copie distante des sauvegardes attend une destination choisie. Les traitements
qui demandent explicitement une heure fixe conservent leur politique actuelle.
