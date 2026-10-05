# Lot 100 — Échéances et priorités cohérentes

Livraison du 6 octobre 2026. Une offre restée dans le catalogue pouvait encore
compter parmi les priorités après une échéance textuelle dépassée. Le dashboard
réévalue désormais les dates à l'heure de l'instantané, sans changer les données.

Un état commun distingue échéance à venir, dépassée, contradictoire ou inconnue.
Une date sans heure reste valable jusqu'à la fin de sa journée de Paris ; un
instant exact est dépassé dès cet instant. Aucune heure employeur n'est inventée.

Les priorités du dashboard et de `stats` excluent les échéances dépassées ; `stats`
exclut également les offres inactives. Le dashboard montre un badge et un filtre
pour les échéances dépassées ; son filtre initial retient les offres actives
sans échéance dépassée. Toutes les offres restent consultables, notamment pour
le suivi des candidatures. Une échéance dépassée ne ferme pas la fiche employeur.
Les contradictions restent visibles et ne deviennent pas des dates certaines.

Validation : tests de frontière à minuit Paris, instant exact, contradiction,
priorités inactives, base vide et lecture sans modification de la base. Régressions
sur dashboard, scanner, rappels, listes Telegram et stockage. Ruff, formatage,
mypy et contrôles JavaScript exécutés avant publication.

Le lot 99 est également publié après l'autorisation explicite du propriétaire.
La validation Windows et les catalogues réels attendent toujours les accès.
