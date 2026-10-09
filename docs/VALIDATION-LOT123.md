# Lot 123 — Raccourcis de suivi sur téléphone

Le formulaire propose « Préparer la candidature » pour une offre active à examiner, « Relance dans 7 jours » pour une candidature au statut Postulé, et « Action terminée » pour retirer la prochaine action et sa date. Les raccourcis préremplissent les champs ; l’enregistrement reste explicite. Les notes, contact, date de candidature et autres champs sont conservés. Les offres inactives, expirées ou déjà envoyées n’ont pas de raccourci de préparation.

Les dates suivent les jours calendaires de Paris, y compris aux changements d’heure et d’année. La logique des raccourcis est isolée dans `tracking.js` et partagée avec le bundle. Les contrôles existants de conflit, relecture après résultat ambigu, historique et abandon du brouillon continuent de s’appliquer. Aucun schéma supplémentaire, candidature automatique ou rappel Telegram supplémentaire.

Validation : quatre tests JavaScript de dates, transitions autorisées et conservation des données. Parcours complet à 390 px sur base synthétique : préparation, confirmation d’abandon, notes conservées, passage à Postulé, relance datée, agenda, persistance après rechargement, action terminée, zéro erreur JavaScript et absence de débordement horizontal. Le départ d’un champ Notes ne supprime plus le bouton avant son clic.
