# Lot 52 — Diplômes visibles dans le dashboard

## Périmètre

La priorité 4 du carnet prévoit l'affichage des prérequis de diplôme. Ce lot
ajoute un filtre **Diplôme mentionné**, un repère dans la liste et les extraits
employeur dans le détail. Le filtre se combine avec entreprise, expérience,
score, recherche et suivi ; Réinitialiser le remet à Tous.

La reconnaissance est limitée aux listes de critères DRW et IMC, placées
immédiatement après un intitulé audité. Les présentations d'entreprise, avantages,
rubriques inconnues, paragraphes libres et autres sources ne sont pas interprétés.
Les rubriques de préférences restent identifiées par leur intitulé original.
Les extraits conservent le texte de chaque critère, avec espaces normalisés.

Les catégories Bachelor / Licence, Master, Doctorat et Diplôme sans niveau précis
décrivent des **mentions**, sans calculer de diplôme minimum. Une annonce peut
figurer dans plusieurs catégories. Préférences, alternatives, négations et dates
de fin d'études restent dans l'extrait : aucun verdict d'éligibilité n'est produit.
Une mention non reconnue ne signifie pas absence d'exigence. Les mots sans contexte
académique, comme « master trading tools » ou « degree of autonomy », sont écartés.

## Mesure sur la copie restaurée

Lecture seule de la copie de sauvegarde utilisée au lot 51 : **773 offres**, dont
**30** avec mention reconnue, **20 DRW et 10 IMC**. Inspection des 30 extraits et
de leurs rubriques. Empreinte du fichier SQLite identique avant et après lecture.

| Catégorie | Offres (catégories non exclusives) |
| --- | ---: |
| Bachelor / Licence | 24 |
| Master | 11 |
| Doctorat | 9 |
| Diplôme sans niveau précis | 5 |
| Aucune mention reconnue | 743 |

Exemples audités : DRW `7996648` accepte PhD ou MSc ; DRW `7730933` place un
diplôme avancé dans Preferred Background sans niveau déduit ; IMC `4704856101`
conserve l'alternative d'expérience pratique ; DRW `8014946` conserve les trois
niveaux et la fenêtre de fin d'études. DRW `7614634`, avec puces textuelles hors
liste HTML prise en charge, reste non reconnu. Aucune exhaustivité revendiquée.

Il s'agit d'une observation calculée au chargement du dashboard ou à l'export.
Aucune migration, réécriture des offres, modification des scores, des candidatures,
des alertes ou des dates de collecte. Aucun nouvel appel aux sources employeur.

## Vérifications

- Suite complète Windows : **3 014 tests réussis, quatre ignorés** (liens
  symboliques indisponibles). Ruff, formatage, mypy et construction du paquet
  installable réussis. Après durcissement des abréviations BS/MS pour exclure
  MS Office, MS SQL et MS Excel : 54 tests ciblés réussis et 30 observations
  auditées identiques.

- Tests des variantes HTML échappées, alternatives, préférences, négations,
  diplôme sans niveau, frontières de rubriques, contenu masqué, doublons,
  mise en forme imbriquée et critères trop longs.
- Test d'intégration du dashboard : toutes les tables et scores conservés.
- Navigateur sur copie : Doctorat = 9, Master = 11, aucune mention = 743 ;
  réinitialisation = 773. Extrait et origine de Quant Researcher vérifiés.
- Mise en page vérifiée sur ordinateur et largeur 390 px : filtre utilisable,
  détail lisible et absence de débordement du formulaire.

## Livraison du 25 septembre 2026

Le lot est publié sur `main` (`f9ea329`, puis durcissement `c2e02ae`). Installation
Windows après sauvegarde vérifiée et conservation du paquet précédent. Les trois
services sont repartis ; le correctif limité à l'affichage redémarre ensuite le
seul dashboard, pendant que scanner et Telegram continuent de fonctionner.

Premier contrôle installé : HTTP 200 pour le dashboard et le suivi des candidatures,
782 offres présentes et 30 avec diplômes reconnus (20 DRW, 10 IMC). Les six preuves
Nomura restent visibles. Scanner actif, collectes réelles HSBC, Macquarie et Crédit
Agricole réussies après reprise à partir de 22:34 Paris.

La différence de volume avec la copie de 773 offres vient des collectes intervenues
entre les deux instantanés. L'observation des diplômes ne crée aucune offre.

Les fichiers installés concordent avec les sources validées. Le contrôle HTTP
après le correctif confirme à nouveau les 30 mentions, le suivi et les six preuves
Nomura. Aucun redémarrage supplémentaire du scanner ou de Telegram n'a été requis.

La [validation GitHub du code final](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36186870819)
est réussie sur Python 3.11 à 3.14 : **3 021 tests réussis**, couverture **96 %**.
La construction Docker et la restauration synthétique sont également réussies.

## Prochain point à traiter

L'exploitation révèle avant ce déploiement une erreur Société Générale
`SG visible reference mismatch` à 22:32 Paris. Auditer le détail renvoyé et sa
référence avant de modifier le collecteur ; ne pas supprimer le contrôle d'identité
ni clôturer des offres sur un échec. Nomura campus dépend toujours du retour d'un
accès public sans challenge. L'extension des diplômes aux autres employeurs demande
un audit séparé des rubriques.
