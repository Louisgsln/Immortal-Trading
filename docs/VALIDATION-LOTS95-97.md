# Lots 95 à 97 - huit employeurs supplémentaires

Extension demandée le 28 septembre 2026, organisée en trois lots cohérents et
livrée ensemble pour limiter les interruptions du scanner. Le périmètre passe
de 78 à **86 sources**, pour **80 employeurs**. Les nouveaux catalogues sont
consultés toutes les **30 minutes**, avec premier import silencieux.

## Sources officielles et périmètre

| Lot | Employeur | Origine officielle vérifiée | Fiches retenues |
| --- | --- | --- | ---: |
| 95 - trading et recherche systématique | Valkyrie Trading | [Carrières](https://www.valkyrietrading.com/careers/), puis fiche Junior Derivatives Trader reliant Lever `valkyrietrading` | 3 |
| 95 | Engineers Gate | [Site employeur](https://www.eglp.com/) et script public `/j/scripts.js` reliant Greenhouse `engineersgate` | 1 |
| 96 - fonds quantitatifs | PDT Partners | [Carrières](https://pdtpartners.com/careers) reliant Greenhouse `pdtpartners` | 1 |
| 96 | Graham Capital Management | [Carrières](https://www.grahamcapital.com/careers/) utilisant Greenhouse `grahamcapitalmanagement` | 1 |
| 96 | Quantbot Technologies | [Carrières](https://www.quantbot.com/careers/) intégrant Greenhouse `quantbot-technologies` | 0 |
| 97 - gestion d'actifs | Wellington Management | [Carrières](https://www.wellington.com/en/careers) reliant [Workday External](https://wellington.wd5.myworkdayjobs.com/External) | 5 |
| 97 | AllianceBernstein | [Carrières](https://www.alliancebernstein.com/corporate/en/careers.html) reliant [Workday](https://abglobal.wd1.myworkdayjobs.com/alliancebernsteincareers) | 1 |
| 97 | Dimensional Fund Advisors | [Carrières](https://careers.dimensional.com/) reliant [Workday DFA Careers](https://dimensional.wd5.myworkdayjobs.com/DFA_Careers) | 0 |

Quantbot publie actuellement huit stages : le catalogue est surveillé, mais ces
stages sont exclus avant import. Dimensional ne retourne actuellement aucun
intitulé retenu dans les recherches trading, trader, quantitative et structuring.
Ces succès avec zéro résultat ne signifient ni panne ni absence de recrutement
chez l'employeur. Le portail institutionnel Dimensional refuse la lecture HTTP
directe ; son lien Workday public a été vérifié depuis la page officielle et le
catalogue Workday a réussi les essais indépendamment.

Toutes ces collectes sont des recherches partielles. Aucun poste n'est fermé
parce qu'il disparaît du périmètre. Les descriptions employeur sont conservées
intégralement ; les formulaires génériques, stages et fonctions de support sont
filtrés. Associate seul reste exclu des priorités, Analyst / Associate conservé.

## Contrôles de collecte

Valkyrie utilise le champ `team`, sans champ `department`, et le contrat
`Full Time`. Le parseur reconnaît cette variante uniquement pour son tableau
vérifié ; les règles Belvedere existantes restent distinctes. Les équipes Trading
et Quants sont retenues, avec validation des UUID, des deux liens candidature et
fiche, des rubriques, de la pagination et des limites de durée et de volume.
`createdAt` n'est pas transformé en date de publication.

Les tableaux Greenhouse vérifient l'employeur, l'identifiant, le nombre de lignes,
les doublons, les métadonnées et le contenu. Graham et Quantbot exigent le chemin
audité et un seul `gh_jid` correspondant exactement à la référence. PDT exige son
champ Employment Type ; aucun grade ni date ne découle du simple nom du tableau.
Les nouveaux Workday réutilisent le collecteur borné et ses validations de
pagination, titre, référence et détails. La couverture n'est pas exhaustive.

## Mesure sur copie

Deux collectes publiques des huit sources ont réussi : **43 requêtes et 12 fiches
reçues à chaque passage**. Le premier ajoute 12 fiches ; le second ne crée aucun
doublon et ne modifie aucune fiche. Aucun conflit, lacune, fermeture ou envoi
d'alerte historique. Les scores des **1 175 fiches préexistantes**, les
candidatures, leurs historiques et les alertes sont préservés.

La revue des descriptions a identifié un faux positif : Credit Trader - Investment
Grade chez AllianceBernstein mentionne **5-7yrs** d'expérience. Une extraction
limitée à cette formulation et à sa rubrique candidat conserve désormais le
minimum de cinq ans ; la préférence IG/HY porte sur l'exposition au marché, pas
sur le nombre d'années. Le poste passe de 73 à **0** sur la copie, avant toute
installation. Deux nouvelles collectes AllianceBernstein vérifient le changement
puis sa stabilité ; les autres fiches, suivis et alertes sont inchangés.

Après ce correctif, le gain est de **12 fiches**, **4 au seuil de 55**, dont
**3 au seuil de 70** :

- Valkyrie, Junior Derivatives Trader : 96 ; la description indique une arrivée
  entre janvier et août 2027 et les conditions d'autorisation de travail aux États-Unis.
- Wellington, EMEA Financing Trader : 77 ; la description demande au moins deux
  ans de trading/sales en repo ou financement garanti G10.
- Valkyrie, Derivatives Trader (European Hours) : 71 ; un an sur un desk de market
  making options est demandé, avec horaires explicités dans la fiche.

**Neuf dates de publication** sont disponibles. Les trois Valkyrie restent sans
date employeur vérifiée. Les descriptions et conditions sont lisibles ; les
rubriques structurées de missions et diplômes ne sont pas encore adaptées à ces
nouvelles sources. Les quatre intitulés de recherche quantitative restent à
qualifier sur preuve de missions, sans promotion globale ni enrichissement IA.

## Pistes non activées

- GSA : les deux postes Quantitative Researcher du flux portent un indicateur
  de poste masqué ; ils ne sont pas importés.
- Voleon : le site officiel pointe désormais sur Ashby ; le contrôle public
  d'accès retourne HTTP 401. Aucun contournement ni activation annoncée.
- Sunrise Futures : portail Trakstar identifié ; adaptateur non encore validé.
- Caxton : portail Workable identifié ; adaptateur non encore validé.
- Capstone : catalogue audité ; postes Associate, stages et assistant en middle
  office ne justifient pas encore une activation pour le ciblage demandé.

## Livraison

Validation locale : **4 649 tests Python réussis, 4 ignorés**, puis les
**17 tests AllianceBernstein** ajoutés après le lancement de la suite complète.
Les 92 cas des deux nouveaux fichiers passent, ainsi que les régressions ciblées
Lever/Greenhouse et Workday/PIMCO/TD. **11 tests JavaScript** réussissent ; Ruff,
le formatage, mypy sur 95 modules et le contrôle du verrou de dépendances passent.
Les 100 fichiers applicatifs du paquet construit correspondent au code source.

La publication, l'installation et l'état réel des services sont consignés
ci-dessous après leur vérification. Ces lots étendent le radar ; ils ne clôturent
pas les autres chantiers de la roadmap.
