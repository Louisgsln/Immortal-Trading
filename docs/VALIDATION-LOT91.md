# Lot 91 — Huit employeurs supplémentaires en finance et trading

Nouvelle vague demandée après les lots 88–90 : **63 sources pour 58 employeurs**,
avec huit catalogues supplémentaires interrogés toutes les **30 minutes**.
Le périmètre couvre banques, gestion d'actifs, exécution et recherche quantitative.

## Sources vérifiées le 27 septembre 2026

| Employeur | Catalogue public retenu | Offres importées sur copie |
| --- | --- | ---: |
| Aquatic Capital Management | [Greenhouse](https://job-boards.greenhouse.io/aquaticcapitalmanagement), lié par [Aquatic](https://aquatic.com/) | 3 |
| Graviton Research Capital | [Greenhouse officiel](https://job-boards.greenhouse.io/gravitonresearchcapital), employeur déclaré « Graviton Research Capital LLP » | 5 |
| AQR | [Portail AQR](https://careers.aqr.com/), intégrant le catalogue Greenhouse `aqr` | 2 |
| Winton | [Greenhouse européen](https://job-boards.eu.greenhouse.io/winton), lié par les [fiches officielles](https://www.winton.com/jobs/4047683101) | 1 |
| WorldQuant | [Greenhouse officiel](https://job-boards.greenhouse.io/worldquant), offres également visibles dans le [catalogue employeur](https://www.worldquant.com/careers/) | 14 |
| G-Research | [Workday G-Research](https://gresearch.wd103.myworkdayjobs.com/G-Research), lié depuis les [fiches officielles](https://www.gresearch.com/vacancies/quantitative-analyst-2/) | 4 |
| ING | [Workday ICSGBLCOR](https://ing.wd3.myworkdayjobs.com/ICSGBLCOR), lié depuis les fiches de [careers.ing.com](https://careers.ing.com/en/job/katowice/senior-java-software-engineer-financial-markets/3121/39507250752) | 0 |
| BlackRock | [Workday BlackRock_Professional](https://blackrock.wd1.myworkdayjobs.com/BlackRock_Professional), lié depuis une [fiche du site officiel](https://careers.blackrock.com/job/shanghai/analyst-quantitative-researcher/45831/94327989472) | 3 |

Les catalogues Greenhouse complets contiennent respectivement 7, 19, 51, 9 et
101 lignes avant filtrage. Les noms, domaines, identifiants, descriptions et
dates sont validés. Les catalogues européens utilisent eux aussi l'API publique
`boards-api.greenhouse.io`. Un champ `metadata: null` est accepté uniquement
sur les quatre nouveaux catalogues où il a été observé ; son absence reste une erreur.

Chez AQR, les 51 liens du flux répètent le même `gh_jid` exactement deux fois.
Ces deux valeurs doivent correspondre à l'identifiant de l'offre : valeur
contradictoire, paramètre supplémentaire ou troisième occurrence interrompent
l'import. Le lien Electronic Trader Analyst a été suivi jusqu'à sa fiche
officielle AQR : redirection vers un chemin descriptif avec un seul `gh_jid`,
page HTTP 200 intégrant le formulaire Greenhouse. Le lien du flux reste conservé.
Le champ employeur **« Post Job? » doit être explicitement `true`**.
`false` et `null` ne permettent pas l'import ; un champ absent ou mal typé
signale un changement de format. Ainsi, le « 2027 Trading Analyst » marqué
`false` n'est pas présenté comme une nouvelle ouverture.

G-Research utilise deux recherches (`quantitative`, `trading`). ING et BlackRock
en utilisent quatre (`trading`, `trader`, `quantitative`, `structuring`).
Les limites restent 500 résultats par recherche, 80 fiches Workday et 600 secondes.
La pagination et l'identité des détails sont contrôlées. ING n'a actuellement
aucune offre retenue : le poste marketing mentionnant le trading est écarté,
mais les futures offres du portail seront surveillées. Ce portail public et
celui de BlackRock ne garantissent pas la couverture de plateformes campus distinctes.

## Résultat et ciblage

Deux collectes du périmètre final sur une nouvelle copie de la base :

- **8/8 sources réussies**, **41 requêtes par passage** ;
- **32 nouvelles offres**, puis **0 nouvelle offre** au second passage ;
- **6 offres pertinentes** (seuil 55), dont **3 prioritaires** (seuil 70) ;
- **32 dates de publication**, **12 fiches avec missions**, **18 avec indications de diplôme** ;
- **1 093 anciens scores inchangés**, suivi et historique conservés,
  aucune alerte créée, aucune fermeture déduite d'une absence.

Les trois priorités sont les Junior Execution Trader WorldQuant à New York et
Singapour (92), et Electronic Trader Analyst AQR (88). Les descriptions demandent
respectivement au moins un an et un à trois ans d'expérience pertinente ; les
conditions complètes restent visibles. Un score ne garantit pas l'éligibilité.

Le filtrage écarte marketing, ingénierie, stages, Summer Analyst et viviers de
candidats. Associate seul reste exclu des alertes, Analyst / Associate reste
admissible aux autres critères. Les postes quantitatifs non encore qualifiés
restent à score nul ou sous le seuil selon les règles existantes ; leur simple
présence chez un fonds ne les promeut pas en poste de trading.

Les rubriques de fiche reprennent des intitulés réellement observés. Elles
conservent les alternatives et préférences et ne modifient aucun score.
Les descriptions sans rubrique reconnue restent disponibles en entier.
La date de première publication est utilisée, jamais la date de modification.
Les tris et filtres de dates du dashboard existants s'appliquent aux nouvelles offres.

Premier import silencieux, collecte partielle sans fermeture par absence,
robots et espacement par hôte conservés. Aucune candidature, inscription
employeur ou notification de test n'a été envoyée.

## Suite

Poursuivre les banques et fonds supplémentaires, notamment les accès publics
de Balyasny et NatWest, ainsi que les portails campus distincts. NatWest a répondu
HTTP 403 lors de cet audit : il n'est pas activé. Qualifier séparément les rôles
quantitatifs et d'exécution encore à zéro, avec preuves de missions et contre-exemples.
Les pistes énergie et l'exploitation restent au carnet. Aucun enrichissement IA
ni comparaison avec le CV n'est réintroduit.


## Vérification locale

**4 345 tests Python réussis, 4 ignorés**, dont **92 tests ajoutés** pour les
identités, liens, visibilité AQR, requêtes des trois portails Workday, filtres
et extraits des nouveaux employeurs. Ruff et son contrôle de format réussis
sur 257 fichiers, mypy sur 93 modules ; **11 tests JavaScript réussis**.
Le paquet construit hors réseau a été comparé aux 98 fichiers applicatifs
du dépôt. Les copies de bases, captures, configurations locales et sauvegardes
ne font pas partie du commit.


## Installation vérifiée

Commit applicatif `b57f36f8a940a1dd7ca767172a09aa544e8839b4`, publié sur `main` et installé le
**27/09/2026 · 21:51** après sauvegarde vérifiée. Les huit collectes du
paquet installé ont réussi : 32 offres, 41 requêtes, aucune alerte historique.
Les 98 fichiers applicatifs installés correspondent au paquet construit.

Contrôle à **27/09/2026 · 21:53** : **1125 offres**,
**331 pertinentes**, **203 prioritaires**,
**673 dates de publication**, **518 fiches avec missions**,
**440 avec indications de diplôme**. Scanner actif, dashboard
et API du suivi accessibles, services programmés relancés. Le suivi, les anciens
scores et l'historique des alertes sont conservés ; premier import silencieux.
À 22:05, 44 sources existantes ont réussi une collecte automatique après la reprise.

Le dashboard rechargé a été vérifié dans le navigateur : nouveaux employeurs,
fiches, liens de candidature, tri de publication et filtres de dates.
ING figure dans la santé des sources avec zéro offre retenue. Les filtres ont
été réinitialisés et aucune candidature n'a été modifiée.

Dernier contrôle à **27/09/2026 · 22:05** : **63/63 sources à jour**.
Toutes les sources sont à jour.

Tous les [contrôles GitHub du commit applicatif](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36345787412) ont réussi :
Python 3.11, 3.12, 3.13 et 3.14, tests JavaScript, construction de l'image et
exercice de sauvegarde/restauration en conteneur isolé.
