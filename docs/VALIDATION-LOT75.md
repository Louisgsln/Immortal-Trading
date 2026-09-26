# Lot 75 — Cinq employeurs, six portails officiels

## Portails et périmètre mesuré le 26 septembre 2026

| Employeur et page officielle | Catalogue public | Retenues | Prioritaires |
|---|---|---:|---:|
| [DV Trading](https://dvtrading.co/join-dv/) | Greenhouse `dvtrading` | 21 | 12 |
| [Walleye Capital](https://walleyecapital.com/careers) | Greenhouse `walleyecapital-external-fulltime` | 4 | 1 |
| [Squarepoint Capital](https://www.squarepoint-capital.com/open-opportunities) | Greenhouse `squarepointcapital` | 13 | 4 |
| [Chicago Trading Company](https://www.chicagotrading.com/search) | Greenhouse `chicagotrading` | 3 | 1 |
| [CTC campus](https://www.chicagotrading.com/campus) | Greenhouse `chicagotradingcampus` | 5 | 1 |
| [Belvedere Trading](https://www.belvederetrading.com/open-positions-1) | Lever `belvederetrading` | 4 | 2 |

Squarepoint publie le nom du catalogue dans le composant chargé par son site.
Les pages de poste CTC incorporent le tableau Greenhouse correspondant, avec
un catalogue campus séparé. Les six sources sont configurées à cinq minutes,
avec concurrence et temporisation partagées selon les règles du scanner.
Le temps réseau et les échecs peuvent espacer les collectes davantage.

227 annonces publiques avant filtrage, 50 retenues. Walleye « Trading & Risk »
et « Quantitative Research & Development » sont des annonces génériques :
la configuration cible les postes définis. Les intitulés senior, expérimentés,
support et infrastructure sont écartés. Une annonce collectée peut rester hors
cible dans le dashboard ; les stages et Associate seuls ne déclenchent pas d'alerte.

## Fiabilité et données conservées

Greenhouse vérifie l'employeur attendu, le catalogue complet et chaque identité.
Squarepoint exige deux paramètres `id` et `gh_jid` concordants, sans paramètres
supplémentaires ; son contrat et sa catégorie d'expérience doivent être cohérents.
Les catégories campus n'annulent pas les exclusions Associate/stages.
Les métadonnées de contacts internes ne sont ni importées ni mises en fixtures.

Belvedere utilise un adaptateur public Lever dédié : UUID, domaine, catalogue,
URL d'offre et de candidature contrôlés ; catégories, contrat et description
vérifiés. Seul le département Trading entre dans la sélection. Pagination bornée,
détection de doublons et relecture de la première page sur plusieurs pages :
un changement ou un échec interdit l'import partiel. Les règles d'accès et
l'espacement des requêtes passent par le client commun.

Les catalogues filtrés ne ferment aucune offre par absence. Le premier import
est silencieux. Greenhouse fournit 46 dates de publication originales ; les
quatre dates Belvedere restent inconnues : `createdAt` ne documente pas une
publication. Aucune date de début ni échéance n'est inventée.

## Fiches et ciblage

Rubriques de missions et qualifications auditées sur les six sources : 33 fiches
supplémentaires avec missions et 25 avec mentions de diplôme. Belvedere rassemble
ses listes structurées sans perdre les mots visibles ; les passages non reconnus
restent dans la description complète. Préférences et alternatives sont conservées.

Six règles bornées couvrent Junior Quant Researcher, ML Alpha Research, Junior
Quant Developer et Graduate Quant Developer chez Squarepoint, Systematic
Quantitative Researcher PhD chez CTC campus, et un Quantitative Researcher chez DV.
Chaque règle exige l'employeur, le titre, la source officielle, les limites de
rubrique et plusieurs preuves de missions. Les mots de présentation de la société
et le contenu masqué ne suffisent pas. Desk Quant Analyst chez Squarepoint reste
hors cible : les missions auditées décrivent suivi de production et opérations.
Les règles ne dispensent ni des qualifications ni du contrôle d'expérience.

## Simulation et validation

Sauvegarde vérifiée puis restauration séparée : les 923 annonces précédentes,
leurs candidatures, historiques et alertes restent identiques. Deux imports
successifs donnent 50 ajouts puis zéro ajout/modification, aucune fermeture et
aucune alerte. Résultat : **973 annonces, 282 pertinentes et 175 prioritaires**.
Les nouvelles sources ajoutent 29 pertinentes et 21 prioritaires.

Les six adaptateurs ont réussi une collecte publique réelle (deux requêtes chacun,
politique d'accès et catalogue). Les tests couvrent identité, métadonnées, contrats,
dates, confidentialité, pagination répétée ou changeante, budgets et ciblage.
Le navigateur vérifie les nouveaux employeurs, le détail Belvedere avec ses
missions et sa publication inconnue, ainsi que les stages à zéro point.

Suite complète Windows : **3 908 tests réussis, quatre ignorés**. Mypy (86 modules),
Ruff et formatage réussis ; dix tests du tri des dates réussis sous Node.

## Livraison et observation

Publié sur `main` : `117f73d701bac039fff3cbb9d64d5c405d746cae`, installé à
20:35:38 Paris après la sauvegarde vérifiée `scheduled-20260926T183532828309Z.zip`.
Les 90 fichiers applicatifs et ressources correspondent au paquet construit.
Scanner, Telegram et dashboard redémarrés ; chaque nouvelle source a réussi
deux collectes. Le premier passage ajoute 50 offres sans alertes ; le deuxième,
achevé à 20:41:46, ne crée ni ajout ni modification.

Contrôle à 20:42:56 : 973 offres, 282 pertinentes, 175 prioritaires, 295 missions,
329 mentions de diplôme et 523 dates de publication. Les scores et candidatures
des 923 offres précédentes, ainsi que les historiques et alertes, sont identiques
à la sauvegarde. Dashboard et API de suivi répondent ; le navigateur vérifie
les 13 offres Squarepoint triées par publication décroissante.

39 sources sur 40 sont à jour. Nomura campus a repris ; HSBC professionnels a
interrompu une pagination dont le total avait changé à 20:37:16. Le lot 76
traite ce cas par une reprise bornée de tout le catalogue. Ces états sont datés
et ne garantissent pas la disponibilité permanente des portails.

Python 3.11–3.14, dashboard et conteneur ont tous réussi en
[CI](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36263044034).
