# Lot 55 — Missions lisibles dans Telegram et le dashboard

## Périmètre

Première étape du résumé des postes prévu en phase 3 : jusqu'à trois extraits
de missions dans la langue de l'annonce, sans génération ni traduction.
Les rubriques auditées de DRW, IMC et HSBC professionnels remplacent les
introductions commerciales dans les prochaines cartes Telegram. Le détail
du dashboard affiche les mêmes extraits complets et leur rubrique d'origine.

Les listes DRW/IMC doivent suivre immédiatement un titre de missions reconnu.
La variante employeur IMC `YOUR CORE RESPONSIBILTIES` est explicitement prise
en charge. HSBC utilise trois couples de rubriques délimitées :
`Purpose of the Job → Environment of the Job`,
`Les grandes lignes → Profil recherché` et
`In this role you will → To be successful in this role you should meet the following requirements`.
Une limite absente, répétée ou inversée, plusieurs sections reconnues, un item
vide ou trop long entraînent un repli vers la description habituelle.

La carte distingue **Missions · extraits** et **Extrait de description**.
Chaque extrait Telegram est limité à 240 caractères, avec une ellipse visible.
Le dashboard conserve les trois premiers items complets (1 500 caractères
maximum par item) ; les conditions et sous-listes restent attachées à leur item.
Ce sont des extraits, jamais une présentation exhaustive des missions.

## Mesure sur sauvegarde restaurée

- **784 offres**, dont **54** avec missions reconnues : **26 DRW, 25 IMC,
  trois HSBC professionnels**.
- Exemple HSBC Securities Lending : l'extrait décrit le prêt de titres clients
  et son cadre de risque, au lieu de l'introduction « Opening up a world… ».
  Le poste reste exclu en tant qu'Associate seul ; afficher ses missions dans
  le dashboard ne le rend pas éligible aux alertes.
- Trois offres DRW/IMC restent sans extrait reconnu : leurs listes ne suivent
  pas une rubrique auditée, ou la description ne contient pas de liste.
- Les 30 observations de diplôme sont identiques à la version précédente
  malgré la mutualisation du lecteur de listes HTML.
- Base entière comparée avant/après : aucun changement des offres, scores,
  candidatures, alertes ou autres tables. Aucun envoi réseau pendant l'audit.
- Toutes les cartes du corpus sont valides et sous la limite Telegram :
  maximum observé **978 unités UTF-16** après interprétation du HTML.

## Vérifications et livraison

Les tests couvrent les titres audités, rubriques ambiguës, bornes HSBC,
contenus cachés, sous-listes, négations et alternatives conservées, repli
explicite, échappement HTML, taille UTF-16 avec emoji et lecture seule du
dashboard. Le suivi Postulé conserve son parcours et ses contrôles existants.

Rendu navigateur contrôlé sur ordinateur et viewport mobile 390 × 844 :
trois missions lisibles sur l'offre HSBC Repo, provenance visible, aucun
débordement horizontal du détail. La description complète reste accessible.

**3 119 tests Windows réussis, quatre ignorés** (liens symboliques indisponibles),
dont 50 nouveaux tests ciblés. Ruff, formatage et mypy réussis.
Publication et déploiement : résultats consignés après livraison.
