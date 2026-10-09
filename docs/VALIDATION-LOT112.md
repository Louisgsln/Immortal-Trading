# Lot 112 — Pays, durée et début

Les filtres combinables utilisent les localisations annoncées, une durée explicite en mois et les dates/périodes de début de l'employeur. Ils ne changent pas les identités des offres.

- Pays : localisations multiples et noms/pays reconnus, avec une option « Pays non reconnu ».
- Durée : mois écrits en chiffres ou en lettres, intervalles et informations contradictoires. Une durée d'expérience ou de candidature n'est pas une durée de stage.
- Début : jour exact lorsqu'il est explicitement fourni, mois ou année dans les autres cas. Les fenêtres se filtrent par chevauchement inclusif ; les mois séparés gardent leurs intervalles distincts. Les dates inconnues/contradictoires sont exclues d'une période sélectionnée.
- Les dates de publication et de diplôme ne deviennent pas des dates de début. Les preuves restent lisibles dans la fiche.

Tests Python des observations, tests Node des filtres et des bornes, contrôle du rendu/du cache et vérification HTTPS du Dashboard. Publication séparée après le lot 111, avec sauvegarde et conservation de la base, des historiques et de Telegram.
