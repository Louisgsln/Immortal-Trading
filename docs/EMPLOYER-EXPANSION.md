# Extension des employeurs — septembre 2026

Dix employeurs officiels ajoutés au lot 73 : **34 sources et 30 employeurs**
activés au total, contre 24 sources et 20 employeurs auparavant.

## Portails vérifiés

Les pages ci-dessous établissent le lien avec le catalogue Greenhouse public.
Chaque réponse complète est contrôlée avant le filtrage local des intitulés.

| Employeur et preuve officielle | Catalogue | Offres sélectionnées |
|---|---|---:|
| [Akuna Capital](https://akunacapital.com/careers/) | akunacapital | 11 |
| [Maven Securities](https://www.mavensecurities.com/jobs/) | mavensecuritiesholdingltd | 10 |
| [Point72 / Cubist](https://careers.point72.com/) | point72 | 29 |
| [Virtu Financial](https://www.virtu.com/careers/) | virtu | 19 |
| [Tower Research Capital](https://tower-research.com/roles/) | towerresearchcapital | 22 |
| [Old Mission](https://www.oldmissioncapital.com/careers/) | oldmissioncapital | 17 |
| [Schonfeld](https://www.schonfeld.com/careers/) | schonfeld | 9 |
| [Five Rings](https://fiverings.com/careers/) | fiveringsllc | 5 |
| [Hudson River Trading](https://www.hudsonrivertrading.com/careers/) | wehrtyou | 10 |
| [TransMarket Group](https://www.transmarketgroup.com/careers) | transmarketgroup | 4 |

Pour HRT, le nom du catalogue est publié dans le script du composant carrières
`wp-content/plugins/hrt-jobs/scripts/frontend-bundle.min.js` chargé par la page.
Point72 et Cubist constituent une seule source et un seul employeur compté.

## Périmètre

- Trading, market making, structuring et recherche/développement quantitatifs.
  Une collecte ne garantit pas qu'une offre soit compatible : le score et ses
  exclusions restent visibles. 52 des 136 offres franchissent 55 points,
  dont 29 franchissent 70, sur la photographie du 26 septembre.
- Les intitulés explicitement expérimentés, fonctions de support, fiabilité,
  infrastructure et événements Women in Trading sont écartés dans ces sources.
  Les Trading Assistant audités chez Five Rings et Schonfeld, et Central Trading
  Analyst / Production Trader chez Tower, attendent une qualification distincte.
- Stages et Associate seuls restent exclus des alertes. Analyst/Associate garde
  la règle du propriétaire. Une catégorie campus ne fournit aucune date de début.
- Les métadonnées de contrat sont contrôlées chez Akuna, Old Mission, Five Rings,
  HRT et Point72 ; les indices junior viennent uniquement de catégories explicites.
- La recherche quantitative sans Trading dans le titre n'est promue que si une
  liste de missions vérifiée lie explicitement construction de modèles ou signaux
  et stratégies de trading. Le paragraphe de présentation de la société ne suffit pas.
- Les missions et études sont des extraits de rubriques employeur vérifiées,
  avec préférences et alternatives conservées. Les passages non reconnus restent
  dans la description complète ; pas d'enrichissement IA ni de comparaison CV.

## Fiabilité et limites

685 annonces dans les catalogues publics avant filtrage, 136 retenues, sur dix
lectures réelles de deux requêtes chacune (politique robots et catalogue).
Identifiants uniques, total intégral, employeur, domaine, chemin et identifiant
de candidature doivent correspondre. Un changement de format provoque un échec
explicite, jamais un import incomplet silencieux. Les prospects sont écartés.
Les métadonnées nulles ne sont admises que sur les portails où elles ont été observées.

135 dates de publication originales sont disponibles ; une reste inconnue.
`updated_at` n'est jamais transformé en date de mise en ligne. Aucune échéance
ou date de prise de poste n'est inventée. Les listes filtrées ne servent pas
à fermer des offres par absence.

Le premier import est silencieux. Les offres restent consultables immédiatement
dans le dashboard ; les prochaines nouveautés éligibles suivent les alertes habituelles.
Les sessions sont séparées et l'espacement des requêtes Greenhouse est partagé.

## Extensions encore à auditer

Squarepoint, Qube, G-Research et Balyasny ont été examinés mais ne sont pas activés
par ce lot : catalogue non complètement validé ou accès automatisé restreint.
Quantlab a répondu HTTP 403. Aucun de ces employeurs n'est compté comme surveillé.
Poursuivre avec les banques, courtiers, fonds et négociants énergie/matières premières,
en conservant une preuve officielle et une simulation d'import par source.
