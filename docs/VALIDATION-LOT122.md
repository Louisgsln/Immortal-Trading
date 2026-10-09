# Lot 122 — Activité du radar et récapitulatif dans le Dashboard

L’accueil affiche le signal réel du radar, sa phase et la date de l’observation. Un signal absent, arrêté, ancien ou une collecte prolongée reste explicite. Le raccourci « Voir les sources » ouvre leur état détaillé. Le réglage du récapitulatif Telegram est consultable, avec son heure de Paris ; un réglage ne constitue pas une preuve de livraison ni d’activité du bot.

La lecture des préférences est bornée à 32 Kio, strictement validée et limitée aux champs utiles. Le Dashboard ne reçoit ni identifiant du destinataire, ni curseur, ni liaison Telegram, ni secret. Le modèle partagé `DigestState` est indépendant des listes d’offres et du notifier, ce qui supprime la dépendance circulaire entre affichage et livraison. Les formats de fichiers, la programmation et la règle d’une tentative quotidienne restent identiques.

Validation : préférences valides, absentes, corrompues, incomplètes, trop volumineuses ou invalides ; ancien signal ; absence de modification des fichiers ; absence des champs privés dans l’affichage. Navigation et rendu vérifiés dans un navigateur à 390 px. Les preuves communes de tests et déploiement figurent dans `DELIVERY-LOTS122-124.json`.
