# Lot 113 — Suivi mobile modifiable et échéances

Le même lien HTTPS privé ouvre le Dashboard sans identifiant ni mot de passe. Le détenteur du lien peut désormais modifier les statuts, notes, contacts, dates et prochaines actions.

L'API publique est limitée au suivi des candidatures. Le backend reste sur loopback, derrière le chemin privé Caddy. La passerelle injecte un secret indépendant du lien ; une session de 24 h utilise un cookie Secure/HttpOnly/SameSite=Strict, un jeton CSRF lié à la session et une origine HTTPS exacte. Les exports HTML et l'éditeur local gardent leurs modes existants. Les contrôles de santé enregistrés ne sont pas exposés en écriture distante.

Les modifications sont atomiques et limitées aux tables applications/application_history. Une révision compare les versions pour éviter d'écraser une modification Telegram ou faite sur un autre appareil. Le brouillon est conservé en cas de conflit ou d'indisponibilité. Les transactions courtes du suivi peuvent coexister avec la collecte ; elles n'envoient aucune candidature ni notification.

Sur téléphone : cartes sans défilement horizontal, champs adaptés au tactile, boutons de sauvegarde accessibles, vue des prochaines actions et dates limites par semaine/mois/retard. Les candidatures déjà déposées ne remontent plus comme échéances de dépôt. Affichage des jours en heure de Paris.

Vérifications : tests d'origine/session/CSRF, expiration et redémarrage, champs invalides, conflits et historique ; navigateur Chromium à 390 px avec filtres combinés, sauvegarde et persistance d'une note/action, agenda et absence d'erreur JavaScript. Intégration Caddy HTTPS sur des données synthétiques avant publication. Aucun essai d'écriture fictive dans la base de production.

Déploiement distinct avec sauvegarde vérifiée. Le lien, les certificats, les alertes et le curseur Telegram sont conservés ; les cinq services restent configurés pour redémarrer automatiquement.
