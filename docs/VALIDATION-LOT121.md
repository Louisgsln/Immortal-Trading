# Lot 121 — Récapitulatif quotidien Telegram compact

Le récapitulatif garde une seule date et un seul bilan des découvertes sur 24 heures. Chaque carte expose l’employeur, le score, le titre, le lieu et un lien cliquable Voir l’offre. L’expérience et la date limite sont présentes seulement lorsqu’elles sont renseignées ; les échéances précises conservent leur horaire en heure de Paris et les dates seules indiquent l’absence d’heure. La hiérarchie explicite ville/continent/pays/administration est raccourcie en ville et pays, tandis que les autres formats de localisation sont conservés.

Le pied du message tient sur une ligne Sources à jour et /status. Les listes tronquées conservent le nombre réel de correspondances. Les noms, titres et liens sont échappés avant l’envoi HTML ; les URLs ne sont jamais coupées. Le récapitulatif et son aperçu /digest utilisent le même rendu HTML. La sélection, le score minimum, l’horaire et la limite d’une tentative quotidienne ne changent pas. Les commandes /new et /top ainsi que les alertes individuelles conservent leur présentation.

Validation : 174 tests Telegram digest/listes/contrôle/candidatures et 2 tests notifications/export réussis. Ils vérifient les limites de message, les liens complets, l’échappement HTML, les fuseaux et changements d’heure, la reprise après redémarrage, l’absence de double envoi et la conservation des tables. Ruff et mypy des modules concernés réussis. Aucun message d’essai envoyé au compte Telegram.

Déploiement avec sauvegarde vérifiée ; contrôle de conservation des données, historiques, alertes envoyées, curseur, horaire et activation du récapitulatif, et de sa dernière tentative. Le blocage sudo est rétabli après les opérations.
