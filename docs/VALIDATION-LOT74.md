# Lot 74 — Incidents compréhensibles et ciblage des missions opérationnelles

## Fiabilité et lisibilité

Le dashboard affiche l'intervalle de chaque source, sa première heure de reprise
possible et le délai appliqué après échec. Le calendrier utilise la même règle
que le scanner, et ne promet ni disponibilité du site ni démarrage à la seconde.
Une date incohérente n'est pas transformée en calendrier valide. L'état reste
daté du chargement ; il faut recharger la page pour actualiser les sources.

Les échecs possèdent une explication courte : CAPTCHA, refus d'accès, limite de
requêtes, délai dépassé, pagination, format ou erreur du portail. Les détails
bruts de transport et les paramètres d'URL ne sont jamais repris dans cette
explication. La commande Telegram `/status` reprend la cause et la reprise possible.
Aucun message de test n'est envoyé lors de la validation.

Macquarie : la redirection publique exacte vers sa page `/en_US/careers/Error`
est identifiée sans suivre la redirection ni importer une liste vide. Ce
diagnostic ne résout pas l'indisponibilité du serveur employeur.

## Ciblage mesuré

Une sauvegarde vérifiée des 923 annonces a été restaurée séparément. Sept scores
changent, six offres sortent du périmètre pertinent, dont cinq prioritaires :

| Poste | Avant | Après |
|---|---:|---:|
| UBS — Trader Assistant | 73 | 0 |
| BNP — Institutional Sales Trading Assistant | 71 | 0 |
| Morgan Stanley — Investment Management, Trading Assistant, Analyst | 86 | 0 |
| Morgan Stanley — Asia Rates Trading Assistant | 73 | 0 |
| Morgan Stanley — MSIM Emerging Markets Trading Assistant, Analyst | 84 | 0 |
| Crédit Agricole CIB — Middle Officer Support Trading Equity | 66 | 0 |
| Nomura — Trading Support | 92 | 84 |

Les cinq premiers cas exigent un employeur, un titre et plusieurs missions
opérationnelles dans une rubrique délimitée, vérifiés sur les annonces. La règle
Middle Officer complète Middle Office. Nomura décrit une fonction de technologie
quantitative liée au trading : elle reste retenue, avec 22 points de métier au
lieu de 30. BNP FX Derivatives Trading Assistant Manager conserve ses 75 points,
car ses missions portent sur la gestion des positions et le pricing.

Les mots Assistant ou Support ne sont pas exclus globalement. Les règles
Associate seul, Analyst/Associate et stages restent inchangées. Un second
recalcul ne change rien. Candidatures, historiques et alertes restent identiques.
Résultat : 923 offres, 253 pertinentes et 154 prioritaires.

## Contrôles

- 36 nouveaux tests : classement des échecs, calendrier, récupération après
  succès, dates invalides, redirections non suivies et cas de ciblage.
- Tests ciblés de santé, scanner, Telegram, dashboard et ciblage réussis.
- Mypy, Ruff et formatage réussis ; tableau de santé vérifié dans le navigateur
  sur une copie de la base avec les incidents réels Nomura et Macquarie.
- Suite complète Windows : **3 826 tests réussis, quatre ignorés**.
- Publication et observation après installation à consigner à l'issue de la livraison.
