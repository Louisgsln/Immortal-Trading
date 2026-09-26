# Lot 62 — Dates de publication, tri et période

## Périmètre

- Colonne **Publiée le** et repère dans le détail de chaque offre, distincts de
  la première détection et de la dernière observation.
- Deux tris de publication, plus récentes et plus anciennes, avant pagination.
  Les dates inconnues restent à la fin ; égalités départagées par titre puis ID.
- Filtre de période avec deux bornes inclusives facultatives, combinable avec
  les autres filtres et la vue Candidatures. Date manquante exclue d'une période.
- Période invalide expliquée sans appliquer le filtre de date ; réinitialisation
  complète et retour à la première page après changement.
- Même comportement sur le serveur local et dans l'export HTML autonome.

Le jour vient exclusivement du `date_posted` conservé par le collecteur,
normalisé en UTC. Aucune heure précise n'est revendiquée : le modèle historique
ne distingue pas toujours une date seule d'un instant. Le navigateur ne décale
pas ce jour vers son fuseau local. Valeur absente, sans fuseau ou hors plage UTC :
**Non précisée**, sans remplacement par une date de découverte ou mise à jour.
Le format d'instantané reçoit un champ additif `publication_day` ; les anciens
jeux de données sans ce champ restent affichables. Aucune migration SQLite.

## Impact sur sauvegarde restaurée

- 787 offres : 342 dates renseignées et 445 non précisées, sur 14 sources datées.
- 11 tables strictement inchangées ; tous les champs précédemment exposés par
  le dashboard restent identiques, notamment scores, échéances et candidatures.
- Aucune collecte, candidature ou alerte déclenchée par l'audit ou les filtres.

## Vérifications locales

- Neuf nouveaux cas Python : date absente, jours UTC, décalages positifs/négatifs,
  année bissextile, date sans fuseau et dépassements aux limites du calendrier.
- Dix tests JavaScript : deux sens du tri, inconnues, égalités, bornes inclusives,
  bornes uniques, dates impossibles, remise à zéro et quatre fuseaux horaires.
  Exécution dédiée sous Node 22 dans la CI ; Node n'est pas requis en exploitation.
- Navigateur sur données synthétiques : tri complet et pagination, inconnues en
  fin de liste dans les deux sens, période inclusive, journée unique, borne seule,
  Candidatures, résultat vide, période inversée, détail et réinitialisation.
- Navigateur sur copie réelle : 48 offres depuis le 20 septembre ; dates de
  publication et de découverte distinctes, présentation vérifiée, aucune erreur JS.
- Suite complète Windows : 3 331 tests réussis, quatre ignorés ; vérifications
  Ruff, formatage et types réussies. Dix tests JavaScript réussis.

## Livraison

- Code `79be0e9` publié sur `main` et installé le 26 septembre 2026 à 12:55 Paris,
  après sauvegarde vérifiée à 12:55:01 ; paquet précédent conservé.
- Les six fichiers applicatifs installés correspondent au paquet publié.
- Dashboard et API de suivi disponibles : 787 offres, 342 dates connues,
  445 inconnues ; 102 missions et 77 diplômes conservés, ainsi que le ciblage
  Associate seul exclu / Analyst-Associate explicitement accepté.
- Parcours sur l'instance active : période du 20 au 25 septembre, 48 offres,
  tri récent/ancien et détail de publication vérifiés sans erreur JavaScript.
- Scanner, dashboard et Telegram redémarrés et actifs. Collectes HSBC campus,
  Crédit Agricole, Macquarie, Optiver et Barclays réussies après installation.
  Les 24 sources sont à jour au contrôle de 12:55:57 ; historique disponible.
- [CI du lot](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36237190361)
  réussie sur Python 3.11–3.14 : 3 335 tests Linux, couverture 96 %. Dix tests
  JavaScript réussis sous Node 22 ; construction et restauration Docker réussies.

## Suite du carnet

Poursuivre les rubriques employeur auditées et l'observation continue des sources.
Les dates encore inconnues nécessitent un champ de publication public vérifiable ;
elles ne seront pas estimées à partir de la collecte.
