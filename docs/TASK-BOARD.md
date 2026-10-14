# Carnet des tâches — 14 octobre 2026

Ce carnet suit l’instance OVH. Un connecteur développé ou une offre visible dans
un catalogue public ne sont pas, à eux seuls, une preuve de surveillance active.
Les validations et mesures sont dans [VALIDATION-LOTS125-127.md](VALIDATION-LOTS125-127.md),
[AUDIT-EMPLOYERS-20261010.md](AUDIT-EMPLOYERS-20261010.md),
[VALIDATION-LOT128.md](VALIDATION-LOT128.md) et
[VALIDATION-LOTS129-131.md](VALIDATION-LOTS129-131.md) et
[VALIDATION-LOTS132-138-139.md](VALIDATION-LOTS132-138-139.md). L'inventaire actuel
est [daté par source](RADAR-SOURCES-LOTS156-158.md) : 91 sources / 79 employeurs,
85 à jour au relevé de 16:45 UTC du 12 octobre. Les chiffres des livraisons précédentes restent historiques.
Ce carnet a été réconcilié avec le VPS :
les anciennes mentions Windows et exclusions globales des stages étaient historiques.

| Priorité / tâche | État | Preuve / prochaine action |
|---|---|---|
| Publier les lots 108–124 | Fait | `53127f2` sur main ; CI 38031223402 réussie |
| Radar et Telegram H24, HTTPS privé, suivi mobile | Installé | Lots 108–124 ; vérifier à chaque déploiement |
| Mesurer découvertes, scores et alertes hebdomadaires | Installé et vérifié | Lot 125 : sept jours, raisons de blocage ; découvertes distinctes des alertes envoyées |
| Réconcilier couverture dépôt / VPS | Installé | Lot 126 : 25 → 63 sources ; profil VPS public distinct |
| Ajouter les employeurs de trading et recherche | Installé et vérifié | 38 sources vérifiées deux fois et initialisées ; 307 fiches / 78 au seuil / 69 à examiner, import sans alerte |
| Corriger les contrats Old Mission et Point72 | Installé et testé | Valeurs publiées `Intern` et `Part Time`, autres valeurs inconnues refusées |
| Retenir la recherche Old Mission liée aux décisions de trading | Installé et testé | Missions vérifiées ; intitulé ou texte d’entreprise seuls insuffisants |
| Réconcilier les scores historiques | Corrigé | 33 champs dérivés réconciliés, 11 scores ; sauvegarde vérifiée, zéro alerte créée |
| BNP Paribas | Général bloqué ; campus partiel installé | Deux fiches stage et 14 lacunes ; recherches refusées conservées au carnet 141-B |
| Optiver | Couverture partielle explicite | Une fiche Trading Automation Specialist non vérifiable ; aucune fermeture déduite |
| Workday existants | Reprise observée, à surveiller | Citi, Deutsche Bank, Morgan Stanley et Barclays frais au contrôle final ; garder les erreurs de pagination/503 explicites si elles reviennent |
| Intitulés quantitatifs rejetés chez Jump et Flow Traders | À qualifier sur missions | Jump 8027898 off-cycle 2027 ; Flow PhD Graduate Quantitative Researcher : annonce complète et contre-exemples avant élargissement |
| Recherche Point72 collectée mais non qualifiée | À auditer | Cubist Quantitative Researcher et variantes : score nul sans preuve de missions retenue ; ne pas attribuer des points au seul intitulé |
| Nomura campus | CAPTCHA observé le 11/10 | Intervention humaine en attente selon le choix du propriétaire ; anciennes fiches conservées |
| Nomura professionnels | Pagination récente à surveiller | Import interrompu sur pages incohérentes ; reprise selon la cadence normale, accès campus distinct |
| Bank of America campus / off-cycle — lot 129 | Installé et observé | Premier succès OVH, 10 fiches ; Milan 15033 à 96/100 et référence bancaire 7/7 |
| Banques comparables — lots 129–130 | Installé et observé | Bank of America (deux portails), Jefferies, RBC, ING, Wells Fargo et Santander ; 70 sources / 62 employeurs |
| Campus complémentaires — lot 132 | Installé et observé | Citi, Deutsche Bank, Lazard ajoutés ; Barclays élargi sur son portail existant |
| Hedge funds — lot 138 | Installé et observé | Millennium campus et Capula ; stages 2026 et candidatures spéculatives hors alertes 2027 |
| Inventaire Telegram — lot 139, extension 11/10 | Installé et observé | `/statuts` = `/status` ; 79 sources / 67 employeurs, `/sources` paginé, même profil que le Dashboard |
| Autres banques, courtiers et énergie non inclus au profil VPS | À faire | Lots suivants : relire les portails depuis OVH et valider avant activation |
| Alertes off-cycle / stages longs 2027 | Activées et vérifiées | 38 fiches satisfont les critères au contrôle ; année/formats conservés ; premiers imports silencieux |
| Réponse du Dashboard avec davantage de sources | Installé et vérifié | CPU 1 du lot 128 conservé ; HTTPS 12.549 s avec 70 sources (129), puis 12.712 s avec 75 (132) ; regroupement des lectures prévu au lot 135 |
| Regrouper les lectures de conflits et lacunes | À mesurer | Profilage du lot 128 : lectures par source encore coûteuses ; conserver toutes les preuves de santé |
| Sauvegarde hors VPS | Destination à définir | Sauvegardes locales automatiques existantes ; aucune destination distante choisie |

Chaque livraison clôture ses lignes après tests, sauvegarde vérifiée, installation
et observation. Les compteurs de premier import ne doivent pas être présentés
comme un nombre garanti de nouvelles offres par semaine.

## Livraison du 12 octobre — lots 148–150

Dernière livraison : [lots 151–153](VALIDATION-LOTS151-153.md), avec [preuves](DELIVERY-LOTS151-153.json).
Trois points Telegram par jour à 09:00, 13:00 et 18:00 Europe/Paris ; six sources supplémentaires,
49 fiches importées sans alerte rétroactive. Les versions HSBC restent stables ; données et curseur préservés.

| Lot | État | Résultat observé |
|---|---|---|
| 148 — HSBC, localisation | Installé et vérifié | Ordre des villes ignoré dans la comparaison ; vraie ville ajoutée/retirée toujours signalée ; six versions historiques conservées après une nouvelle collecte |
| 149 — État Telegram quotidien | Installé et vérifié | Bloc radar même sans offre, programmation indépendante des erreurs de réception ; envoi du 12/10 confirmé, confirmation distincte envoyée une fois |
| 150 — Contrôle du worker H24 | Installé et vérifié | Radar sain malgré les problèmes de couverture explicitement conservés ; 79 sources programmées, 73 à jour, zéro redémarrage au contrôle final |

[Validation](VALIDATION-LOTS148-150.md) et [preuves](DELIVERY-LOTS148-150.json).
Base, alertes, suivi et curseur Telegram préservés ; même Dashboard HTTPS privé.
Le digest reste activé à 09:00, heure de Paris ; `/statuts` donne le nombre et l'état courant.

Le lot 147 reste ouvert : au relevé initial de 13:20 UTC le 12/10, Goldman campus, Point72 et Morgan Stanley campus
ont retrouvé un état à jour. Morgan Stanley professionnels est partiel ; Citi campus est en échec récent.
Diagnostiquer ces détails et collectes, suivre leur reprise, puis revalider les témoins avant clôture.
BNP général/campus et Jefferies campus restent en difficulté ; Nomura campus attend toujours
l'intervention humaine choisie par le propriétaire. Aucune erreur n'est assimilée à un catalogue vide.
Citi campus et Morgan Stanley professionnels sont à jour dans le relevé des lots 151–153 à 14:16 UTC.
Ces reprises ne clôturent pas le suivi des autres accès en difficulté.

## Livraison du 11 octobre — 141-A et 143-A

79 sources / 67 employeurs, 72 à jour à `2026-10-11T15:34:40.063998+00:00` ; 70 nouvelles identités,
71 associations, zéro alerte initiale. [Inventaire complet](RADAR-SOURCES-20261011.md),
[validation](VALIDATION-INTEGRATIONS-20261011.md) et [preuves](DELIVERY-INTEGRATIONS-20261011.json).
Les quatre nouveaux périmètres ne fournissent encore aucun stage 2027 au seuil entièrement admissible.
Brevan off-cycle générique et Rothschild GMS/advisory sont ajoutés à l'audit métier 133.

## Lots bancaires demandés le 10 octobre

| Lot | Travail et résultat attendu | Validation avant clôture | État |
|---|---|---|---|
| 129 — Bank of America campus | Collecteur distinct des professionnels et événements ; témoin Global Markets Sales and Trading 2027 Off-Cycle Analyst – Milan | Catalogue entier paginé, identités et fiches employeur concordantes ; score expliqué ; Summer et événements exclus des alertes | Installé et observé ; Milan 96/100 |
| 130 — Autres banques | Jefferies campus, RBC, ING, Wells Fargo et Santander vérifiés ; JPMorgan campus reste HTTP 403 | Deux lectures cohérentes par source ; offres off-cycle/longues documentées ; contrats et année conservés sans inférence | Installé et observé ; sept ajouts réussis |
| 131 — Suivi de couverture | [Carnet par portail](BANK-CAMPUS-COVERAGE.md) et [sept témoins](BANK-CAMPUS-REFERENCE.json) ; conversions CDI séparées du stage, mois alternatifs conservés | Tests de régression, premier import sans envoi, ancienne base/historique/curseur préservés, premiers succès en production | Livré ; témoins 7/7, données préservées |

### Lots complémentaires et prochaines tâches

Les lots marqués « À faire » ou « À développer » réservent les prochaines livraisons ;
leur numéro ne constitue pas une preuve d'installation. Les lots clos ci-dessous
ont été observés sur OVH. Chaque lot présente son avant/après et ses limites.

| Lot / priorité | Travail concret | Critère de clôture | État / dépendance |
|---|---|---|---|
| 132 — campus complémentaires | Citi campus sur Workday, Deutsche Bank étudiants sur Beesite/Recsolu, Lazard étudiants Oracle CX_2 ; Barclays passe à six recherches | Catalogues et détails concordants ; programme et conversion CDI distincts ; premiers imports OVH, données et alertes préservées | Installé et observé |
| 133 / haute — missions quantitatives | Auditer Jump 8027898, Flow PhD Graduate Quantitative Researcher, Cubist/Point72, Bank of America 14722, Jefferies 1954 et DB Central COO Global Markets (80/100) et Millennium Trading Services Intern (90/100), Brevan off-cycle générique (0) et Rothschild 539 GMS/advisory (78) | Responsabilités employeur positives et contre-exemples ; score expliqué sans points tirés de la présentation générale ; aperçu historique, sauvegarde puis réconciliation silencieuse | À faire ; fiches déjà repérées |
| 134 / haute — stages et dates | Auditer les formats/années inconnus ING et Santander ; rendre durée, mois alternatifs, graduation et langues exploitables dans les filtres existants | Valeur et extrait employeur concordants ; inconnu reste inconnu ; Summer et mauvais millésime restent hors alertes ; contrôle Dashboard et tests sur fiches réelles | À faire ; sources 130 |
| 135 / moyenne — architecture Dashboard | Mesurer les lectures de conflits/lacunes par source puis les regrouper ; comparer la réponse mobile avant/après sur la même base | Temps et nombre de lectures consignés ; santé, preuves de lacunes, statuts, notes et révisions identiques ; contrat du Dashboard et HTTPS privé vérifiés | À mesurer ; performance 128 conservée |
| 136 / moyenne — couverture dans le temps | Comparer découvertes, programmes éligibles, causes de rejet et alertes réellement envoyées sur sept jours ; enrichir la référence de témoins indépendants | Rapport daté par portail ; imports initiaux séparés des nouveautés ; absence d'un témoin devenue tâche explicite, aucune fausse promesse de débit hebdomadaire | À faire après une semaine d'observation |
| 137 / moyenne — sauvegarde distante | Choisir une destination puis définir rétention et restauration sur copie isolée | Destination autorisée, archive vérifiée et restauration testée ; base, historiques et état Telegram conservés | En attente de destination ; sauvegardes locales actives |
| 138 — hedge funds publics | Millennium campus Eightfold et Capula Workable public ; distinguer offres ouvertes, stages et viviers | Pagination/compte et fiches vérifiés deux fois ; premier succès OVH ; témoin off-cycle 2026 détecté sans alerte 2027 ; poste spéculatif exclu | Installé et observé |
| 139 — inventaire et commandes privées | Alias `/statuts` et `/statut`, `/sources` et pages suivantes ; sources actives, fraîcheur et employeurs distincts | Total identique au Dashboard, inventaire complet sans doublons et messages dans la limite Telegram ; contrôle propriétaire et curseur conservés | Installé et observé |
| 140 / haute — banques UK restantes | [Standard Chartered](https://www.sc.com/en/global-careers/early-careers/) SuccessFactors, Lloyds Industrial Placements et NatWest | Lien employeur officiel, catalogue entier, détails et offre ouverte dans les métiers ; 403 explicite si persistant, aucun faux catalogue vide | Standard Chartered robots interdit au contrôle 11/10 ; Lloyds à raccorder, NatWest refusé |
| 141 / haute — banques FR | 141-A : Rothschild étudiants et BNP campus installés ; 141-B : BPCE/Natixis et accès BNP restants | Rothschild 60/60, six détails ; BNP deux fiches et 14 lacunes ; données préservées | 141-A observé, BNP partiel ; 141-B ouvert ; [preuve](VALIDATION-INTEGRATIONS-20261011.md) |
| 142 / haute — banques US restantes | Reprendre JPMorgan campus si accès public ; auditer familles campus Citi, Wells Fargo et autres banques/boutiques pertinentes | Témoins indépendants d'off-cycle/longs retrouvés ; bornes de requêtes publiées ; ni 403 contourné ni missions de front office inventées | À auditer ; complément de 129–132 |
| 143 / haute — fonds supplémentaires | 143-A : Millennium professionnels et Brevan Howard installés ; 143-B : Balyasny, Rokos, Citadel et Two Sigma | 46 et 17 fiches ; provenance officielle, pagination et détails ; Brevan off-cycle année inconnue | 143-A observé ; 143-B ouvert ; [preuve](VALIDATION-INTEGRATIONS-20261011.md) |
| 144 / haute — témoins de stages | Ajouter Citi Markets Paris 2027, Deutsche Bank Global Markets et placements longs à la référence indépendante ; structurer durée/début/graduation/langues ; qualifier le Citi LATAM Analyst Program 2025 encore affiché à 70 | Identités et extraits employeur conservés ; Summer/mauvais millésime exclus ; conversion CDI conditionnelle distincte, année inconnue non inventée | À faire ; complète 134 et les régressions 132 |
| 145 / moyenne — export de couverture | Comparer sources, employeurs, associations d'offres, programmes admissibles et alertes envoyées sur sept jours | Utiliser `job_sources` pour les portails communs Citi ; dédupliquer les offres ; distinguer import initial, découverte et publication | À faire ; complète 136 et l'inventaire 139 |
| 147 / haute — reprise des sources critiques | Goldman campus : rôle incomplet/incohérent ; Point72 : timeout ; Morgan Stanley campus : échec récent | Diagnostiquer la fiche et le contrat employeur, retrouver un témoin ; aucun faux succès ni fermeture par absence | Ouvert le 11/10, [relevé](RADAR-SOURCES-20261011.md) |
| 148 — stabilité HSBC | Comparer les adresses multiples indépendamment de leur ordre et rendre la localisation lisible | Historique réel et permutations sans nouvelle alerte ; vraie ville modifiée détectée ; observation OVH | Installé et vérifié le 12/10 |
| 149 — état quotidien Telegram | Afficher activité, couverture et seuil dans le récapitulatif, même sans offre ; isoler la programmation des erreurs de réception | Préférences et curseur préservés, une tentative par jour, envoi confirmé | Installé et vérifié le 12/10, 09:00 Europe/Paris |
| 150 — santé du worker | Distinguer activité du radar et accès aux employeurs dans le contrôle Docker | Worker sain ; signal ancien/base inaccessible toujours en échec ; problèmes de sources visibles | Installé et vérifié le 12/10 ; 73/79 à jour au relevé |
| 151 — points d'état réguliers | États à 13:00 et 18:00 en plus du digest de 09:00, avec tentatives persistantes séparées du curseur | Redémarrage, échec Telegram, DST et chevauchement du digest sans doublon ; propriétaire et réglages conservés | Installé et vérifié ; confirmation envoyée, prochain point 18:00 le 12/10 |
| 152 — cohérence et signal | Recontrôler la première page Workday paginée sur les six ajouts, Citi campus et Morgan Stanley ; vérifier les références campus ; capturer le signal avant les contrôles lents | Changements de catalogue refusés, ordre/âge d'affichage tolérés ; aucune fermeture par absence ; signal cohérent | Installé et vérifié ; Citi campus et Morgan Stanley relus avec succès |
| 153 — six employeurs | PIMCO, BlackRock, CIBC, TD, G-Research et TP ICAP | Deux lectures puis revalidation, simulation, import silencieux, premier succès, conservation et CI | Installé et observé ; 49 fiches, 85 sources / 73 employeurs |
| 154 / haute — qualification des nouveaux portails | CIBC FICC 2619877 : filtre de titre et NON_TRADING malgré pricing/execution/booking clients ; autres intitulés pertinents rejetés | Responsabilités et exigences vérifiées, contre-exemples contrôle/opérations ; changements métier mesurés sur copie avant réconciliation silencieuse | À faire ; complète le lot 133 ; aucune inflation de score au lot 153 |
| 155 / moyenne — ressources SQLite | Diagnostiquer le ResourceWarning Python 3.14 de connexion non fermée, localiser l'allocation et vérifier les fermetures lors des exceptions | Trace d'allocation puis test de non-fuite pertinent, CI complète | À diagnostiquer ; 5 347 tests passent sur les quatre versions |

### Incidents et contrôles récurrents

| Tâche | Action / preuve attendue | État |
|---|---|---|
| BNP, JPMorgan campus et NatWest | Reprendre selon les accès publics disponibles ; conserver HTTP 403 explicite et anciennes fiches, sans contournement | Ouvert |
| Nomura campus | Surveiller les succès publics ; laisser l'intervention humaine en attente si CAPTCHA, conformément au choix du propriétaire | Surveillance ; accès campus distinct des professionnels |
| Workday et Nomura professionnels | Suivre dernier succès, erreur et reprise de pagination ; un résultat nul n'est valide qu'après un catalogue cohérent | Surveillance |
| RBC `markets` | Contrôler le volume par requête (482/500 lors de l'audit) ; étudier une partition publique si le plafond est atteint | Surveillance, import tronqué interdit |
| Déploiements | Sauvegarde vérifiée, import silencieux sur copie, alertes et suivi préservés, curseur Telegram non réinitialisé, mêmes liens privés | À chaque livraison |

Pour chaque nouveau portail, consigner : URL officielle, accès observé, périmètre,
pagination, identifiant employeur, offre témoin, date du dernier contrôle et preuve
du premier succès OVH. Une erreur d'accès reste une tâche ouverte et ne vaut pas
absence d'offres. Les étapes de livraison sont : développé → testé → installé →
observé ; seule la dernière permet de marquer une source comme surveillée.

## Lots 156–158 — installés et vérifiés le 12 octobre

| Lot | État | Résultat observé |
|---|---|---|
| 156 — Toutes les nouvelles offres | Installé et vérifié | Envoi automatique de chaque nouvelle offre collectée et vérifiée, tous scores, même 0 ; import initial silencieux ; `/offres` paginé pour les archives |
| 157 — Liste de souhaits partagée | Installé et vérifié | Bouton Telegram signé, favoris indépendants des candidatures, vue mobile compacte avec filtres repliables, tri, retrait et Postulé ; notes/actions via le suivi existant ; synchronisation de la page ouverte toutes les dix secondes |
| 158 — Six portails supplémentaires | Installé et vérifié | BP, Shell, Marex, Wellington Management, AllianceBernstein, Arrowstreet Capital ; deux lectures stables ; 21 fiches initialisées sans alerte rétroactive ; 91 sources / 79 employeurs |
| Passerelle HTTPS des souhaits | Corrigé et vérifié | Routes wishlist et confirmation Applied autorisées uniquement sous le lien privé ; 13 tests ; certificats, session, origine et CSRF conservés |

[Validation](VALIDATION-LOTS156-158.md), [preuves](DELIVERY-LOTS156-158.json), [inventaire](RADAR-SOURCES-LOTS156-158.md).
Les cinq services Docker tournent, le radar et le Dashboard sont sains ; les quatre services système sont actifs et activés au démarrage.
Une carte Telegram réelle à 0 avec bouton des souhaits a été envoyée une fois avec accusé de réception. Les horaires 09:00, 13:00 et 18:00 Paris restent configurés.
Base principale en schéma 4, anciens identifiants, candidatures, historiques, alertes envoyées et curseur préservés. Les favoris sont sauvegardés dans la même archive version 2 que la base principale.

Prochains lots :

- 159 — réduire le délai de chargement du Dashboard : 18,6 secondes au contrôle HTTPS de 1 581 fiches, puis 22,4 secondes pour 1 591 fiches au lot 162 et 26,6 secondes pour 1 683 fiches au lot 164, puis 39,64 secondes pour 1 729 fiches au lot 166 ; profiler les lectures/parsers avant de modifier la fraîcheur des données.
- 160 — documenter et compléter la couverture Marex, actuellement sept fiches validées sans inventaire exhaustif ; conserver l'absence de fermeture déduite.
- 161 — suivre les échecs datés Bank of America et TD en plus des accès BNP général/campus et Jefferies campus ; Nomura campus attend toujours l'intervention humaine choisie.

Les lots 154 (qualification CIBC FICC) et 155 (avertissements SQLite des tests Python 3.14) restent ouverts. Le flux tous scores n'élargit pas à lui seul les filtres de collecte des portails.

## Lot 162 — informations des opportunités (installé et vérifié)

Demande du 13 octobre : remplir localisation, début, expérience et échéance avec les informations officielles disponibles.

- Fiche UBS 351976 / référence 344425BR vérifiée sur le portail officiel : intitulé actuel eFX Crypto Trader, Singapour ; expérience préalable en entreprise d'actifs numériques ou desk eFX, sans ancienneté chiffrée ; aucune date de début ni de clôture publiée.
- Extraction commune : critères d'expérience non chiffrés et leurs qualificatifs conservés, dates françaises, début exact quand explicitement publié, ASAP/à convenir et recrutement au fil de l'eau sans date inventée.
- Pays/cités supplémentaires reconnus ; anciennes identités et localisations stockées conservées pour éviter les fausses actualisations.
- Même information dans Telegram et Dashboard, extraits et date réelle de vérification ; cache ne fige pas cette dernière.
- Audit initial : 1 573 offres actives ; 178 pays non reconnus, 1 387 débuts inconnus, 1 113 anciennetés minimales non reconnues, 1 522 échéances inconnues. Absence de publication et difficulté d'extraction sont distinguées.

Tests ciblés, contrat des assets, contrôle mobile, simulation sur copie, sauvegarde version 2 et installation sont vérifiés. Les 1 591 fiches bénéficient du nouvel affichage ; 1 575 actives au relevé, dont 105 critères d'expérience non chiffrés. Base, candidatures, alertes, souhaits et historiques, digest, curseur et liaison Telegram préservés. Une fiche UBS corrigée envoyée une fois avec réception confirmée. [Validation](VALIDATION-LOT162.md) · [Preuves](DELIVERY-LOT162.json).

Suite — lot 163 : analyser par source les valeurs encore à interpréter (62 débuts, 34 échéances et 72 localisations au relevé), chercher les champs structurés officiels manquants et conserver les ambiguïtés tant qu'aucune preuve ne les tranche. Les conflits de dates ne seront pas remplacés par l'année courante. Le lot 159 de performance du Dashboard et les reprises d'accès du lot 161 restent ouverts.


## Lot 164 — six sources supplémentaires (installé et vérifié)

State Street, Mizuho, Northern Trust, LSEG, GSA Capital et Quadrature Capital. Profil VPS installé : 97 sources / 85 employeurs, 89 à jour au relevé daté. /statuts et Dashboard concordent. [Sources et limites](RADAR-SOURCES-LOT164.md).

258 tests ciblés, Ruff et Mypy réussis ; 5 424 tests par version Python 3.11–3.14, 34 tests JavaScript et récupération du conteneur réussis ; six contrôles CI verts sur le correctif. Deux lectures stables, puis revalidation complète supplémentaire. Simulation sur copie : 67 fiches, 2 à score ≥ 70 et 59 à 0 ; seconde importation sans création ni actualisation ; zéro alerte et zéro appel Telegram. Identifiants, candidatures, journaux et souhaits conservés ; sauvegarde/restauration version 2 vérifiée.

La fraîcheur insuffisante de la première référence a empêché son installation ; code et configuration rétablis, sans restauration de la base. Relance réussie sur nouvelle lecture identique et sauvegarde vérifiée ; 67 nouvelles fiches, zéro actualisation historique et zéro alerte à l’import. Les 15 contrôles de préservation passent, cinq services Docker tournent et les quatre services système sont actifs/activés. Même accès privé HTTPS et API des souhaits/candidatures vérifiées. [Validation](VALIDATION-LOT164.md) · [Preuves](DELIVERY-LOT164.json).

Suite — lot 165 : qualifier les titres non retenus par les recherches, notamment Credit Derivatives Sales chez Mizuho, et compléter les portails régionaux/campus. Chaque élargissement sera basé sur les missions publiées ; aucun point attribué au nom d'une banque. BNY reste à traiter sur la pagination ; les portails 403 et les viviers restent distincts des sources actives. Les lots 159, 160, 161, 163, 154 et 155 restent ouverts.

## Lot 166 — six employeurs supplémentaires

Scotiabank, D. E. Shaw, T. Rowe Price, Aberdeen, Invesco et Trafigura. Deux nouveaux collecteurs officiels et quatre profils Workday. 41 fiches initiales vérifiées ; 217 tests ciblés, 34 JavaScript, Ruff/formatage et Mypy passent. État : installé et observé le 14 octobre. Trois lectures stables ; simulation et sauvegarde/restauration vérifiées ; 41 fiches, dont 7 à score ≥ 70 et 31 à zéro, importées sans alerte. Profil VPS : 103 sources / 91 employeurs, 91 à jour au relevé ; les six ajouts sont à jour. `/statuts` et Dashboard concordent. Les 15 contrôles de préservation passent, mêmes liens privés et souhaits/candidatures modifiables ; cinq conteneurs actifs, radar et Dashboard sains, quatre services système actifs/activés ; sudo à nouveau bloqué. Les 5 466 tests locaux et les 5 466 tests sur chacune des quatre versions Python 3.11–3.14 passent. [Sources et périmètre](RADAR-SOURCES-LOT166.md) · [Validation](VALIDATION-LOT166.md).

## Prochaines intégrations

| Lot / priorité | Travail et preuve attendue | État |
|---|---|---|
| 167 / haute — banques et campus | Qualifier BMO Phenom, Janus Henderson SuccessFactors et Schroders Oracle, puis les programmes campus Scotiabank ; retrouver les fiches front office dont le titre ne contient pas trading ; inventaire, pagination, deux lectures, fiches témoins et simulation | À faire ; ne sont pas comptés comme nouveaux portails actifs |
| 168 / haute — fonds supplémentaires | Aspect Capital : redirection officielle vers Hibob ; Balyasny : portail Salesforce publié ; Rokos : retrouver un catalogue officiel exploitable ; séparation des programmes informatifs, viviers et postes ouverts | À faire ; accès restreints et CAPTCHA laissés explicites |
| 165 / haute — qualification | Mesurer les faux négatifs et les intitulés de support retenus chez les nouveaux employeurs, dont Mizuho Credit Derivatives Sales et Scotiabank ; justifier toute extension par les missions, sans bonus de score au nom de la société | Ouvert ; le flux tous scores ne remplace pas la qualification des fiches |

Les lots 154, 155, 159, 160, 161 et 163 restent ouverts. Nomura campus reste en attente conformément au choix du propriétaire. Chaque portail n'est déclaré surveillé qu'après installation et premier succès observé sur OVH ; `/statuts` doit concorder avec le Dashboard et l'inventaire installé.
