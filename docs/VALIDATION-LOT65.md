# Lot 65 — Missions et diplômes Barclays

## Périmètre audité

Les 17 descriptions Barclays conservées ont été inspectées. Les missions
proviennent uniquement de la liste **Accountabilities** : jusqu'à trois éléments
complets dans le dashboard, extraits bornés dans les prochaines alertes éligibles.
Les attentes générales du grade et les parcours conditionnels Sales/Trading ne
sont pas substitués à cette rubrique commune.

Les diplômes proviennent des listes **Essential Skills/Basic Qualifications** et
du bloc **Who we're looking for**. Pour ce dernier, le titre doit être en gras,
sur sa propre ligne, dans un paragraphe ou un conteneur. Le reste du bloc est
conservé en entier, sans traverser sa limite ; un titre supplémentaire ou une
structure ambiguë empêche l'extraction. Les variantes de Tokyo réparties entre
plusieurs paragraphes restent hors périmètre.

Les formulations « degree or expected degree », « penultimate or final year of
your degree » et « post-graduate degree » sont reconnues uniquement pour cette
source, comme **Diplôme sans niveau précis**. Aucun Bachelor ou Master n'est
déduit d'un cycle, aucune obtention du diplôme n'est présumée. Conditions de
fin d'études, préférences, équivalences et conditions de visa restent dans
l'extrait employeur, sans interprétation supplémentaire.

## Impact sur sauvegarde restaurée

- 787 offres, dont 17 Barclays : 17 nouvelles fiches avec missions et 14 avec
  diplômes (13 sans niveau précis, une Bachelor).
- Couverture totale : 158 missions et 122 mentions de diplôme ; les observations
  de toutes les autres sources sont identiques à la version précédente.
- 11 tables inchangées, ainsi que tous les modèles d'offre : scores, dates,
  candidatures, alertes et historique conservés.
- 787 cartes Telegram vérifiées : HTML valide et maximum de 1 170 unités UTF-16,
  sous la limite de 4 096. Aucune ancienne alerte réémise.
- Les exclusions Associate seuls et stages restent applicables ; une observation
  de diplôme ne rend pas une offre éligible.

## Vérifications locales

- 34 tests ajoutés : listes et titres sur une ligne, limites des paragraphes,
  conditions de fin d'études, préférences, alternatives, contenus masqués,
  ambiguïtés, périmètre par source, limites Telegram et suivi Postulé conservé.
- Parcours navigateur sur copie : Barclays + diplôme sans niveau précis
  (13 offres), détail Graduate Programme 2027 London ; Bachelor (une offre),
  détail Legal GCS Markets. Extraits et rubriques visibles, aucune erreur JavaScript.
- Suite complète Windows : 3 437 tests réussis, quatre ignorés. Ruff, formatage
  et vérification des types réussis.

## Livraison

- Code `1d349ae` publié sur `main` et installé le 26 septembre 2026 à 14:22:21 Paris,
  après sauvegarde vérifiée à 14:22:16 ; paquet précédent conservé.
- Les deux fichiers applicatifs installés correspondent au paquet publié.
- Dashboard et API de suivi disponibles : 158 missions, 122 diplômes, 342 dates de
  publication. Ancienne couverture Citi, Deutsche Bank et Morgan Stanley conservée,
  ainsi que les exclusions Associate et les titres ouverts aux deux niveaux.
- Les deux parcours de filtre et de détail sont aussi vérifiés sur l'instance
  active, sans erreur JavaScript. Scanner, dashboard et Telegram actifs.
- Collectes Crédit Agricole CIB, Macquarie, Optiver et UBS campus/professionnels
  réussies après installation.
  Les 24 sources sont à jour au contrôle de 14:27:50 ; historique disponible.
- [CI du lot](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36241685752)
  réussie sur Python 3.11–3.14 : 3 441 tests Linux, couverture 96 %. Dix tests
  JavaScript sous Node 22 réussis ; construction et restauration Docker réussies.

## Suite du carnet

Poursuivre l'audit des autres employeurs et des variantes encore non reconnues,
dont les paragraphes Barclays Tokyo. Qualifier séparément les rôles hybrides et
maintenir l'observation des sources. La copie distante des sauvegardes attend
toujours une destination choisie.
