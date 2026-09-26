# Lot 61 — Missions et diplômes Goldman Sachs

## Périmètre audité

Les descriptions conservées des 61 fiches `goldman_sachs` ont été inspectées.
Les listes adjacentes aux rubriques suivantes fournissent les missions :
Responsibilities, Key Responsibilities, Job Responsibilities, Role Responsibilities,
Your Responsibilities, Principal Responsibilities, General Responsibilities,
How You Will Fulfil Your Potential et What You Will Do.

Les diplômes proviennent des listes Qualifications, Basic Qualifications,
Preferred Qualifications, Required Qualifications, Required Qualifications and Skills,
Preferred Qualifications and Skills et Basic Qualifications and Preferred Qualifications.
Le titre exact de la rubrique et les phrases complètes conservent les alternatives,
les préférences et l'expérience éventuellement proposée à la place du diplôme.

L'alternative parenthésée « Bachelor or Master » reconnaît les deux niveaux ;
« Master trading tools » ne devient pas un diplôme. Aucun minimum académique
ni décision d'éligibilité n'est calculé. Le score et le ciblage Analyst/Associate
ne changent pas.

Les titres mêlant missions et qualifications, les introductions, les sous-rubriques
non auditées et le portail campus restent hors périmètre. Plusieurs rubriques de
missions reconnues entraînent le repli habituel vers la description. Une liste
masquée n'est plus retenue ni utilisée pour relier un ancien titre à une liste
sans titre : cette correction du lecteur commun protège aussi les sources existantes.

## Impact sur sauvegarde restaurée

- 787 offres, dont 61 fiches Goldman professionnels conservées.
- 36 nouvelles observations de missions ; 66 anciennes conservées, soit 102.
- 32 nouvelles observations de diplôme ; 45 anciennes conservées, soit 77.
- 11 tables strictement inchangées après génération, dont scores, candidatures,
  historique et alertes. Aucune migration, nouvelle collecte ou clôture dans cet audit.
- Toutes les cartes Telegram valident le format HTML et restent sous la limite :
  maximum mesuré de 1 170 unités UTF-16 sur les 787 offres.

Les prochaines alertes éligibles utilisent jusqu'à trois extraits courts ; le
dashboard conserve les phrases complètes et la provenance. Aucune ancienne alerte
n'est réémise, aucun message reçu n'est réécrit. Une fiche hors cible peut gagner
des extraits dans le dashboard sans devenir éligible aux alertes.

## Vérifications

- 54 nouveaux tests : rubriques, contenu échappé, listes imbriquées, alternatives,
  préférences, textes masqués, sections ambiguës, campus exclu, limites Telegram,
  protection du HTML et données inchangées.
- Navigateur sur copie : filtre Goldman + Bachelor et fiche Rates Trader,
  Analyst/Associate, Johannesburg (92/100) ; filtre Master et fiche STS AI Structuring,
  Analyst/Associate, Bengaluru (80/100), avec alternative Bachelor/Master intacte.
  Présentation visuelle et absence d'erreur JavaScript vérifiées.
- Suite complète Windows : 3 322 tests réussis, quatre ignorés. Ruff, formatage
  et vérification des types réussis.

## Exploitation

Goldman professionnels a repris sa collecte le 26 septembre à 12:21 Paris,
avec 60 fiches, sans assouplissement des contrôles de pagination. Les 24 sources
sont à jour au contrôle suivant ; leur disponibilité publique peut varier.
La fiche conservée absente de cette collecte n'est pas déclarée fermée.

Publication et installation après sauvegarde à consigner après leur exécution.

## Suite du carnet

Étendre les rubriques auditées aux autres employeurs, qualifier séparément les
rôles hybrides et poursuivre l'observation des sources. Les sauvegardes distantes
attendent toujours une destination choisie.
