# Lot 63 — Missions et diplômes Citi

## Périmètre audité

Les descriptions conservées des 51 fiches Citi ont été inspectées. Les listes
adjacentes à **Responsibilities**, **Key Responsibilities** et **What you'll do**
fournissent jusqu'à trois missions. Les listes **Education**, **Qualifications**
et **Recommended Qualifications** fournissent les mentions de diplôme.

Le titre de la rubrique et les phrases complètes restent visibles dans le détail.
Les formulations « Bachelor’s degree/University degree or equivalent experience »
et « Master’s degree preferred » conservent leurs alternatives et préférences.
« University degree preferred » reste sans niveau précis ; les études en cours
et « Advanced degree » ne deviennent pas un niveau académique inventé.

Les rubriques mêlant plusieurs sujets, listes sans titre reconnu, prose sans
liste adjacente, contenus masqués et rubriques non auditées restent hors périmètre.
Deux sections de missions reconnues conservent le repli vers la description.
Les autres portails ne sont pas activés par ressemblance avec Citi.

L'aide du dashboard décrit désormais la provenance sans énumération exhaustive
d'employeurs ; le détail conserve le nom réel de la rubrique employeur.

## Impact sur sauvegarde restaurée

- 787 offres, dont 51 Citi : 15 nouvelles fiches avec missions et 20 avec diplômes.
- Totaux : 117 missions et 97 mentions de diplôme ; ancienne couverture conservée.
- 11 tables strictement inchangées, dont offres, scores, candidatures, alertes
  et historique. Aucune migration ni réécriture des dates de publication.
- Les 787 cartes Telegram valident le format HTML ; maximum de 1 170 unités UTF-16,
  sous la limite de 4 096. Les prochaines alertes éligibles utilisent les extraits ;
  aucune ancienne alerte n'est renvoyée, aucun message reçu n'est réécrit.
- Les exclusions habituelles restent appliquées, notamment Associate seul et
  stages hors cible. L'ajout d'extraits ne constitue pas une nouvelle éligibilité.

## Vérifications

- 33 tests ajoutés : libellés et HTML échappé, listes imbriquées, alternatives,
  préférences, diplômes sans niveau, contenus masqués, rubriques ambiguës,
  limites Telegram, protection du HTML et conservation du suivi Postulé.
- Navigateur sur copie : Citi + Master (15 résultats), détail FX Options Trader
  conservant la préférence Master et l'expérience équivalente ; missions du stage
  Off-Cycle Internship, Paris 2027, sans changement de son exclusion existante.
  Présentation visuelle vérifiée, aucune erreur JavaScript.
- Suite complète Windows : 3 364 tests réussis, quatre ignorés. Contrôles Ruff,
  formatage et types réussis ; dix tests JavaScript des dates réussis.
- [CI du lot](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36239027454)
  réussie sur Python 3.11–3.14 : 3 368 tests Linux, couverture 96 %. Dix tests
  JavaScript sous Node 22 réussis ; construction et restauration Docker réussies.

## Livraison

- Code `1f7c80e` publié sur `main` et installé le 26 septembre 2026 à 13:30:59 Paris,
  après sauvegarde vérifiée à 13:30:54 ; paquet précédent conservé.
- Les quatre fichiers applicatifs installés correspondent au paquet publié.
- Dashboard et API de suivi disponibles : 117 missions, 97 diplômes, dont 15 et 20
  pour Citi. Les 342 dates de publication restent disponibles ; le ciblage des
  titres Associate seuls et Analyst/Associate est conservé.
- Navigateur sur l'instance active : filtre Citi + Master, détail FX Options
  Trader, missions de Full Time Analyst London 2027 (90/100), sans erreur JavaScript.
- Scanner, dashboard et Telegram redémarrés et actifs. Collectes XTX, Flow Traders,
  IMC, DRW et SIG réussies après installation. Les 24 sources sont à jour au
  contrôle de 13:31:30 ; historique de santé disponible.

## Suite du carnet

Étendre les rubriques auditées à d'autres employeurs, notamment Morgan Stanley,
Barclays et Deutsche Bank, dont les structures ont été repérées sans être activées.
Poursuivre l'observation des sources et qualifier séparément les rôles hybrides.
Les sauvegardes distantes attendent toujours une destination choisie.
