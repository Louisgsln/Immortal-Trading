# Lot 69 — Critères d'études Crédit Agricole CIB

## Périmètre audité

Deux lectures publiques de 21 annonces le 26 septembre 2026, avec 26 requêtes
par collecte, confirment le champ `fldapplicantcriteria_educationlevel`.
Le collecteur exige son paragraphe simple immédiatement précédé d'un titre h3
**Minimal education level** ou **Niveau d'études minimum**. Le champ et le libellé
sont conservés dans les métadonnées de la description, même sans archive brute.
Les structures masquées, ambiguës ou non reconnues ne donnent pas de preuve.

Le texte visible ne change pas. La collecte suivante peut donc enrichir la fiche
sans créer de changement de contenu ni de nouvelle alerte. Aucune origine n'est
inventée pour les anciennes descriptions non étiquetées.

- Dix fiches : **Bachelor Degree / BSc Degree or equivalent**.
- Dix fiches : **Bac + 5 / M2 et plus**, classées Bac+5 sans Master supposé.
- Une fiche : **Postgraduate degree – MA/MSc/PhD/Doctorate or equivalent**,
  classée Master et Doctorat avec son alternative complète.

Les extraits restent limités à 1 500 caractères et ne constituent aucune décision
d'éligibilité. Le texte d'aide reconnaît qu'une mention peut être une exigence,
une préférence ou une alternative. Les autres champs et Macquarie restent hors
de cette extension.

## Répétition sur sauvegarde restaurée

- 787 offres, 21 descriptions enrichies avec leur provenance ; 187 fiches avec
  critères d'études, 168 missions et 342 dates de publication.
- Les deux captures publiques ont les mêmes valeurs, scores et textes visibles.
- Deux scans successifs sur copie : zéro nouvelle offre, mise à jour, clôture
  ou alerte. Les tables de candidatures, d'alertes et leurs historiques, les
  versions d'offres et l'historique des scores restent strictement identiques.
- Tous les champs métier des offres sont conservés ; seules la description
  structurée et les données normales d'observation de la source sont actualisées.
- Les 787 cartes Telegram sont identiques et valides, maximum 1 170 unités UTF-16.
  Aucun envoi de test ; les exclusions Associate seuls et stages sont conservées.

## Vérifications

- 40 nouveaux tests : provenance bilingue, valeurs complètes, absence d'équivalence,
  structures ambiguës ou masquées, doublons, périmètre par source, persistance sans
  archive brute, suivi Postulé, scans répétés et protection HTML.
- Parcours navigateur sur copie : Bac+5 (dix offres), **Structurer - GMD** à 71/100 ;
  Bachelor (dix offres), **Structured Credit Structuring Analyst** à 82/100.
- Master puis Doctorat : une offre dans chaque filtre, avec l'alternative complète
  MA/MSc/PhD/Doctorate et son libellé employeur. Texte d'aide et affichage vérifiés ;
  aucune erreur JavaScript.
- Suite complète Windows : 3 593 tests réussis, quatre ignorés. Ruff, formatage,
  vérification des types et dix tests JavaScript réussis.

## Livraison

Publication, installation et contrôles GitHub à consigner après livraison.

## Suite du carnet

Préserver les intitulés de champs Macquarie avant d'étendre les critères d'études.
Poursuivre l'audit des tableaux BNP, rubriques UBS mixtes et Barclays Tokyo.
Maintenir l'observation des sources sans assouplir les contrôles de pagination.
