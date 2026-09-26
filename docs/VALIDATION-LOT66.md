# Lot 66 — Diplômes UBS professionnels

## Périmètre audité

Les 36 fiches UBS professionnels conservées ont été inspectées. Le collecteur
préserve les libellés des champs employeur sous forme de titres HTML. La lecture
des diplômes exige une rubrique unique **Your skills and experience**, suivie
immédiatement de **About us**. Le portail campus reste hors périmètre.

Les puces séparées par des sauts de ligne sont reconnues. Chaque extrait conserve
la puce entière et l'éventuelle introduction des critères, notamment lorsqu'elle
précise une préférence ou le contexte du poste. Une structure inattendue, une
puce vide ou une ligne intermédiaire ambiguë empêche l'extraction de la rubrique.
Les sous-titres mixtes et les listes comportant des continuations restent donc
accessibles dans la description complète, sans interprétation de leur portée.

Les formulations explicites « university degree », « law degree » et
« graduate degree » sans niveau précis sont reconnues uniquement pour cette
source. Elles n'impliquent aucun Bachelor ou Master par équivalence. Les diplômes
préférés, les alternatives par expérience, les disciplines et les négations
restent visibles ; un doctorat préféré n'est pas présenté comme un minimum.
Les certifications seules et les expressions non académiques ne sont pas
transformées en diplôme.

## Impact sur sauvegarde restaurée

- 787 offres, dont 36 UBS professionnels : 16 nouvelles fiches avec diplômes.
- Sept mentions Bachelor, deux Master, une Doctorat et sept sans niveau précis ;
  une même fiche peut contenir plusieurs niveaux.
- Couverture totale : 138 offres avec diplôme ; les 158 fiches avec missions et
  toutes les observations antérieures restent identiques.
- Les 11 tables et tous les modèles d'offre sont inchangés : scores, dates,
  candidatures, alertes et historique conservés. Les exclusions Associate seuls
  et les titres ouverts aux deux niveaux ne sont pas modifiés.
- Les 787 cartes Telegram restent valides, avec un maximum de 1 170 unités
  UTF-16. Aucun envoi ni modification d'une ancienne alerte.

## Vérifications locales

- 40 tests ajoutés : limites des rubriques, puces, introductions, préférences,
  alternatives, contenus masqués, structures ambiguës, périmètre par source,
  absence d'équivalence supposée, affichage sûr et conservation du suivi Postulé.
- Parcours navigateur sur copie : UBS + Doctorat (une offre), détail Electronic
  Trading Quantitative Analyst (92/100), mention préférée non obligatoire ;
  UBS + Master (deux offres), détail Product Structuring Specialist (59/100),
  alternative Bachelor/Master et parcours juridique conservés. Aucune erreur JavaScript.
- Suite complète Windows : 3 477 tests réussis, quatre ignorés. Ruff, formatage
  et vérification des types réussis.

## Livraison

Publication, installation et contrôles GitHub à consigner après la validation locale.

## Suite du carnet

Poursuivre l'audit des autres employeurs et des variantes encore non reconnues,
dont les rubriques UBS mixtes et Barclays Tokyo. Qualifier séparément les rôles
hybrides et maintenir l'observation des sources. La copie distante des sauvegardes
attend toujours une destination choisie.
