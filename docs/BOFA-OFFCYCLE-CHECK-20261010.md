# Offre témoin Bank of America — contrôle du 10 octobre 2026

**Correction installée et vérifiée :** le collecteur campus du lot 129 détecte
Milan 15033 à **96/100**, off-cycle 2027 de 3–6 mois ; échéance employeur au
11 octobre 2026. La source a réussi son premier import sans alerte rétroactive.
Voir [les lots 129–131](VALIDATION-LOTS129-131.md) et la référence 7/7.
Les constats ci-dessous décrivent l'état antérieur à cette correction.

La capture transmise par le propriétaire montre **Global Markets Sales and
Trading 2027 Off-Cycle Analyst – Milan**. Ce titre correspond aux métiers et
au format/année demandés ; il constitue un exemple prioritaire de couverture
campus à ajouter. Le score, les conditions de candidature et l'activité actuelle
de la fiche employeur ne sont pas établis par cette capture.

## Constat sur le VPS à 11:44 UTC

Une lecture SQLite avec `mode=ro`, `query_only=ON` et transaction de lecture
relève zéro offre Bank of America, zéro correspondance Global Markets 2027 à
Milan et aucun état de collecte historique Bank of America. La configuration
chargée dans le conteneur radar comporte 63 sources activées, sans source Bank
of America. Les stages off-cycle/longs 2027 et leurs alertes restent activés.
Cette offre précise n'est donc pas détectée par l'instance active.

Le dépôt de développement possède un connecteur Workday professionnel
`bank_of_america`, pour `ghr.wd1.myworkdayjobs.com/lateral-us`. Il n'est pas
inclus dans le profil OVH vérifié et ne couvre pas le portail campus distinct.

## Portail public observé

Les [pages étudiants officielles](https://careers.bankofamerica.com/en-us/students)
et la [recherche étudiants](https://careers.bankofamerica.com/en-us/students/job-search)
répondent HTTP 200 depuis OVH. La recherche porte le marqueur public
`job-source=campus` et charge ses résultats en JavaScript.
L'ancien domaine `campus.bankofamerica.com` redirige vers la page de présentation
campus ; cette redirection n'est pas un catalogue d'offres.

La navigation officielle renvoie aussi à `bankcampuscareers.tal.net`. Le tableau
`candidate/jobboard/vacancy/2/adv/` est intitulé **Campus Events** : ses événements
ne doivent pas devenir des offres de stage. Aucun identifiant d'offre ou lien
de candidature précis n'est déduit de ce tableau.

## Tâche prioritaire au carnet

Identifier le catalogue de postes étudiants et la fiche témoin Milan, vérifier
la pagination, les identifiants, le contenu et les dates, puis ajouter un
collecteur campus distinct. Utiliser l'offre témoin comme cas de régression avec
des contre-exemples : Summer, événements et postes hors cible. Tester le score
et l'éligibilité à partir des missions et conditions employeur, puis installer
avec sauvegarde et premier import silencieux.

Ce contrôle n'a modifié ni la base, ni les historiques, ni les réglages ou le
curseur Telegram. Le blocage temporaire de `sudo` a été rétabli. Aucune nouvelle
source n'a été déclarée active à l'issue du contrôle.
