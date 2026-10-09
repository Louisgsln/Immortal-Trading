# Lot 119 — Filtre année de stage sur téléphone

Ajout d’un filtre indépendant Année du stage, combinable avec programme, pays, durée et début. L’année confirmée dans le titre ou le début annoncé est utilisable même sans mois de début. Les années inconnues et les programmes contradictoires ont des sélections explicites ; ces derniers sont exclus des années confirmées. Une année sélectionnée ne fait pas passer un Graduate pour un stage.

Les raccourcis Off-cycle et Stages longs sélectionnent l’année configurée dans le radar (2027 en production), sans modifier la politique Telegram. Les préférences restent opt-in, limitées à cet appareil et séparées entre Offres et Candidatures. Les années mémorisées absentes de l’instantané sont ignorées. Réinitialiser et oublier fonctionnent aussi pour ce nouveau filtre.

Validation : 272 tests Python Dashboard et 30 tests JavaScript réussis. Navigateur réel à 390 px sur base synthétique : stage 2027 sans mois inclus, années 2026/2027/inconnues/programmes contradictoires séparés, raccourcis, mémorisation et vues distinctes, réinitialisation et absence de débordement horizontal ; zéro erreur JavaScript. Aucune candidature de production utilisée pour les tests.

Déploiement avec sauvegarde vérifiée et contrôles de conservation, même lien HTTPS privé et mêmes services H24.
