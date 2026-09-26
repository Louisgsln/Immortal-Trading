# Lot 83 — Session Nomura dédiée, activation conditionnelle

Le propriétaire souhaite accéder aux offres campus depuis le radar malgré
le CAPTCHA. Le site officiel renvoie vers le même tableau protégé ; aucune
source de remplacement équivalente n'a été validée.

Un mode optionnel réutilise une session de navigateur dédiée au portail public.
Une commande ouvre une fenêtre distincte, attend une validation manuelle et
vérifie le tableau avant de conserver localement les cookies Nomura. Aucune
résolution automatique, aucun compte candidat et aucun profil personnel utilisés.
La dépendance Playwright est optionnelle et verrouillée ; le scanner HTTP ne
dépend pas du lancement permanent d'un navigateur.

Les identifiants, le périmètre, les scores et les règles d'import ne changent pas.
Le cookie et l'agent du navigateur sont appliqués par requête, uniquement à
l'origine HTTPS Nomura ; les en-têtes globaux du transport ne sont pas modifiés.
Les données de session restent hors offres, historiques et export. Fichiers
bornés et remplacés atomiquement ; domaines, chemins, caractères des en-têtes,
dates et expiration sont contrôlés. Le CAPTCHA reste un échec sans import partiel.

Une session renouvelée après un échec permet une unique reprise anticipée ;
un nouvel échec rétablit la temporisation normale. La source reste en échec
tant qu'une collecte réelle n'a pas réussi. Aucun ancien instantané n'est
présenté comme une collecte fraîche.

Les tests couvrent la portée du cookie, son expiration, les fichiers absents
ou invalides, les entêtes malformés, le stockage atomique, l'absence de fuite
dans les offres, la fermeture du navigateur et la reprise bornée après validation.
Le guide [NOMURA-ACCESS.md](NOMURA-ACCESS.md) décrit l'activation et les limites.

Le test réel et l'activation attendent l'accord explicite du propriétaire pour
utiliser Playwright avec une fenêtre dédiée et conserver localement sa session.
Le mode n'est pas activé sur l'instance en l'absence de cette validation.

Validation locale : suite complète **4 025 tests réussis, 4 ignorés** ; les
deux cas ajoutés ensuite sur la reprise après renouvellement ont été validés
avec les 75 tests pertinents de session, planification et explications d'incident.
Format et lint de 248 fichiers, analyse statique de 89 modules réussis.
