# Lot 92 - Banques, gestion d'actifs, fonds et trading indépendant

Nouvelle vague du 28 septembre 2026 : **71 sources pour 66 employeurs**.
Huit nouveaux catalogues toutes les **30 minutes**, avec premier import silencieux.

## Origine et périmètre vérifiés

| Employeur | Catalogue officiel retenu | Offres sur copie |
| --- | --- | ---: |
| Wolverine Trading | [Portail Pinpoint](https://careers.wolve.com/), flux RSS lié par ce portail ; [site employeur](https://www.wolve.com/open-positions) | 4 |
| Gelber Group | [Page employeur](https://www.gelbergroup.com/careers/), catalogue Greenhouse `gelbergroup` | 7 |
| Verition | [Offres officielles](https://www.verition.com/open-positions), catalogue `veritiongroupllc` et nom publié « Verition Group LLC » | 4 |
| Marshall Wace | [Early careers](https://www.mwam.com/join-us/early-careers/), catalogue `mw-tech-grad` et nom publié « Marshall Wace - Graduate & Associate roles » | 1 |
| PIMCO | [Workday pimco-careers](https://pimco.wd1.myworkdayjobs.com/pimco-careers), lié depuis la [page carrières](https://www.pimco.com/us/en/about-us/careers) | 12 |
| CIBC | [Workday search](https://cibc.wd3.myworkdayjobs.com/search), lié depuis la [page carrières](https://www.cibc.com/en/about-cibc/careers.html) | 0 |
| TD | [Workday TD_Bank_Careers](https://td.wd3.myworkdayjobs.com/TD_Bank_Careers), lié depuis les [lignes de métier officielles](https://careers.td.com/finding-a-team/lines-of-business/) | 2 |
| State Street | [Workday Global](https://statestreet.wd1.myworkdayjobs.com/Global), lié depuis le [portail officiel](https://careers.statestreet.com/global/en) | 3 |

Les trois nouveaux catalogues Greenhouse contiennent 9, 26 et 7 entrées avant
filtrage. Leurs identités, liens et dates de première publication sont contrôlés.
`metadata: null` est explicitement observé et accepté pour ces trois catalogues ;
un champ absent reste une erreur. Verition utilise exactement un `gh_jid` dans
le chemin `/open-positions`, égal à l'identifiant de l'offre.

Wolverine publie 15 annonces dans un RSS contenant les descriptions intégrales,
le contrat, le lieu et la date de publication avec décalage horaire. Le collecteur
consomme une seule requête utile par cycle et ne visite pas les formulaires.
Le titre employeur, les identifiants, les en-têtes des fiches, les doublons,
les dates, les limites de taille et de nombre sont vérifiés ; déclarations DTD
et entités XML refusées. L'alias `wolve.wolve.com` présent dans le canal et les
GUID sert seulement de métadonnée. Les liens utilisables sont ceux du flux,
sur `careers.wolve.com`. Le lien numérique du Quantitative Trading Analyst a
été suivi jusqu'à sa fiche publique `/postings/eeca5bb4-977f-4a1e-ac1b-db56de416a8c`,
avec titre confirmé. Aucun cookie personnel ni formulaire de candidature utilisé.

Les quatre catalogues Workday emploient les recherches `trading`, `trader`,
`quantitative` et `structuring`, avec pagination vérifiée, 500 résultats maximum
par requête, 80 détails maximum et 600 secondes par collecte. Les totaux observés
sont respectivement 73/73/53/69 chez PIMCO, 44/44/30/66 chez CIBC et
130/120/62/237 chez TD. Chez State Street, les recherches non filtrées dépassent
500 résultats pour trading/trader : quatre catégories officielles bornent la portée.

| Catégorie State Street | Identifiant public `jobFamilyGroup` |
| --- | --- |
| Capital Markets | `56250981e7cb01de6d22a5893041350c` |
| Investment Management | `56250981e7cb0196f798ca8930414b0c` |
| Development Programs | `56250981e7cb014c5ea0b8893041410c` |
| Sales and Service | `56250981e7cb01951c88df893041570c` |

Ces quatre catégories donnent 47/47/18/24 résultats selon la recherche, avant
filtrage des titres. Les fonctions hors catégories restent hors surveillance.
Toutes les sources de ce lot sont partielles : aucune disparition ne ferme une offre.

## Fiches et ciblage

Les rubriques missions et diplômes sont lues dans les sections effectivement
publiées, avec leurs conditions et alternatives. Cela ajoute **21 fiches avec
missions**, **18 avec diplôme** et **33 dates de publication**. Les mentions
« preferred » restent des préférences. Aucune promotion de score liée au nom
de l'employeur, aucun enrichissement IA ni comparaison avec le CV.

Deux clauses professionnelles échappaient au parseur général : « 8+ years » dans
les exigences du Trader, Investment Grade Credit de PIMCO, et « Minimum five years »
dans les qualifications du Funding Trader TD. Une reconnaissance bornée à ces
employeurs et formulations conserve le minimum publié et applique l'exclusion
existante des postes exigeant au moins cinq ans. Les anciens employeurs ne sont
pas concernés ; textes cachés, histoire de l'équipe, négations et préférences ne
constituent pas cette preuve. Les traders expérimentés Gelber restent visibles :
certaines fiches exigent un historique de rentabilité d'un à deux ans, à lire
dans le détail ; un score de priorité ne signifie pas une candidature débutante garantie.

Associate seul et stages restent exclus ; Analyst / Associate reste admissible.
Le seul poste quantitatif retenu chez Marshall Wace est intitulé Associate :
il reste donc à **zéro**, sans exception pour le nom du programme. Les deux
catalogues professionnels Marshall Wace vides et son catalogue exclusivement
stage ne sont pas ajoutés. Les fonds de candidatures génériques ExodusPoint
ne sont pas présentés comme des vacances de poste. CIBC est suivie avec zéro
offre retenue à cet instant. Les portails campus distincts ne sont pas réputés couverts.

## Mesures sur copie

Deux collectes réelles successives réussies : **33 offres**, **16 pertinentes
au seuil de 55**, **8 au seuil de 70**, **94 puis 95 requêtes utiles**.
Deuxième passage : aucune nouvelle offre, aucune fermeture, aucune alerte créée.
Les huit sources, y compris CIBC à zéro, sont initialisées. Les **1 127 anciennes
offres** gardent scores, desks et classes d'actifs ; suivi des candidatures et
historique des alertes inchangés. La base active reste séparée pendant ces essais.

Les nouveaux tests couvrent le RSS, les trois identités Greenhouse, les racines
et filtres Workday, les limites, les erreurs d'accès et délais, les dates, les
contrats et le maintien des exclusions, ainsi que les sections et les exigences
professionnelles. Validation locale : **4 446 tests Python réussis**, **4 ignorés**, dont
**101 nouveaux tests** ; **11 tests JavaScript réussis**, Ruff sur **261 fichiers**,
mypy sur **94 modules**, verrouillage des dépendances vérifié. Le paquet contient
**99 fichiers applicatifs**, comparés aux sources avant installation.
La preuve d'installation est ajoutée après les vérifications effectives.
