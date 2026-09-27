# Lots 88 à 90 — Diversification des employeurs trading

La priorité demandée est un univers plus large que les matières premières.
Huit employeurs sont ajoutés, en trois lots cohérents, avec une collecte toutes
les **30 minutes**. Le périmètre configuré passe de **47 à 55 sources** et de
**42 à 50 employeurs**. Les autres intervalles de collecte restent en place.

## Lot 88 — Teneurs de marché et trading pour compte propre

- **Mako** : options, actions, taux et change ; catalogue Greenhouse intégré
  dans la [page officielle](https://www.mako.com/opportunities).
- **Geneva Trading** : trading discrétionnaire et quantitatif multi-actifs ;
  catalogue intégré dans les [postes ouverts](https://www.genevatrading.com/careers-open-positions/).
- **Da Vinci** : trading et recherche quantitative, notamment options ;
  identifiant Greenhouse `davinciderivatives` publié dans la
  [page carrières](https://davincitrading.com/careers/).

Ces trois catalogues réutilisent le collecteur Greenhouse borné. Les noms
d'employeur, domaines, chemins et identifiants d'offres sont validés avant
import. `metadata: null` est accepté uniquement pour Mako et Da Vinci, où
ce format a été observé ; un champ absent reste une erreur.

Le lien Mako fourni par l'API contient un segment d'identifiant qui renvoie
HTTP 404. Après validation de ce segment et du paramètre `gh_jid`, le radar
emploie `/opportunities/job-listing?gh_jid=…`, route effectivement liée depuis
le catalogue officiel et vérifiée HTTP 200. Aucune candidature n'est envoyée.

## Lot 89 — Fonds et recherche quantitative

- **Qube Research & Technologies** : exécution, recherche quantitative,
  taux, repo, delta one et actifs numériques. Le
  [catalogue public Greenhouse](https://job-boards.greenhouse.io/quberesearchandtechnologies)
  identifie explicitement l'employeur sur les 200 annonces observées. Le
  collecteur respecte les règles d'accès de l'API publique et n'interroge pas
  la page `/careers/` du site principal, interdite aux robots.
- **Man Group** : trading de produits titrisés, quantitatif, macro, futures
  et change. La [page officielle](https://www.man.com/careers) renvoie au
  [catalogue Greenhouse européen](https://job-boards.eu.greenhouse.io/mangroup).

Les champs de contrat `Employment Type` et `Workforce Sub-Type` sont conservés.
Un stage identifié dans ces champs reste exclu des alertes même si son intitulé
ne contient pas « Intern ». Aucune ancienneté ni date d'entrée n'est inventée.
Les intitulés mélangés Internship/Graduate restent exclus par prudence, comme
les autres stages du radar ; leur séparation éventuelle demande une preuve
d'offre distincte. Les développeurs et ingénieurs ne sont pas ajoutés par
simple proximité avec le trading.

## Lot 90 — Banques de marchés

- **Bank of America** : portail professionnel
  [Workday lateral-us](https://ghr.wd1.myworkdayjobs.com/lateral-us), lié depuis
  le [site carrières](https://careers.bankofamerica.com/en-us/job-search/united-states).
- **RBC** : [portail Workday public RBCGLOBAL1](https://rbc.wd3.myworkdayjobs.com/RBCGLOBAL1),
  dont les fiches identifient RBC et renvoient à [jobs.rbc.com](https://jobs.rbc.com/).
- **Wells Fargo** : [portail public WellsFargoJobs](https://wf.wd1.myworkdayjobs.com/WellsFargoJobs).
  Le lien « Sign In or Create an Account » du
  [site officiel](https://www.wellsfargojobs.com/en/jobs/) renvoie au même
  tenant `wf` et au même catalogue, sur le domaine Workday de recrutement.

Quatre recherches : `trading`, `trader`, `quantitative`, `structuring`.
Limites de 500 résultats par recherche, 80 fiches sélectionnées, 600 secondes.
Pagination, doublons, identité des détails et stabilité des résultats restent
contrôlés par le collecteur Workday existant.

Wells Fargo interprète `structuring` très largement : **668 résultats**, dont
une majorité de banque de réseau. Le radar utilise les quatre catégories
officielles observées, combinées par OU dans la facette `jobFamily` :

| Catégorie | Identifiant public |
| --- | --- |
| Trading | `6cee717ed86e0100b32510f615390000` |
| Advanced Analytics | `1018d766e49a1001be3a1fcd33700000` |
| Investment & Trading Products | `6cee717ed86e0100b3250fc26f7d0000` |
| Early Career Programs | `a474682131921001babf17eb9f800000` |

La couverture est donc partielle et dépend de la catégorisation de l'employeur.
Un poste quantitatif de validation des risques peut rester dans la base avec
un score nul : son titre seul ne le rend pas éligible aux alertes de trading.
Le portail campus distinct de Bank of America n'est pas couvert par ce lot.

## Fiches, ciblage et sécurité du suivi

Les huit employeurs gagnent des rubriques missions et qualifications fondées
sur les intitulés observés dans leurs descriptions. Les extraits conservent
les préférences, alternatives et conditions ; ils ne modifient pas le score.
La première publication Greenhouse est utilisée, jamais sa date de modification.
Les dates passent par les tris et filtres existants du dashboard.

Premier import silencieux, recherches partielles sans fermeture par absence,
espacement minimum de deux secondes par hôte. Associate seul, stages et
conditions d'expérience incompatibles restent exclus des alertes ;
Analyst/Associate reste admissible. Aucun enrichissement IA ou rapprochement
avec le CV. Aucun message de test ni candidature envoyé.

## Validation

Les résultats des collectes, tests et contrôles d'installation sont consignés
ci-dessous après leur exécution.


Deux collectes réelles sur copie de la base : **8 sources réussies sur 8** à
chaque passage, **112 requêtes** puis **112**.
**69 offres ajoutées**, **18 pertinentes**, **13 au seuil de 70**,
**69 dates de publication**, **41 fiches avec missions**, **39 avec indications
de diplôme**. Les **1024 anciens scores** et le suivi sont conservés ;
aucune alerte créée, aucune fermeture déduite et aucun doublon au second passage.

| Employeur | Offres importées |
| --- | --- |
| Mako | 4 |
| Geneva Trading | 4 |
| Da Vinci | 8 |
| Qube Research & Technologies | 22 |
| Man Group | 10 |
| Bank of America | 13 |
| RBC | 7 |
| Wells Fargo | 1 |

Les offres importées ne sont pas toutes éligibles : les seuils et exclusions
continuent de s'appliquer. Les 13 offres au seuil ont également été relues pour
repérer les conditions d'expérience présentes dans les descriptifs ; le score
ne confirme ni l'éligibilité individuelle ni une probabilité de recrutement.

Suite locale : **4253 tests Python réussis, 4 ignorés**, dont **95 nouveaux
contrôles** ; **11 tests JavaScript réussis**, lint et format de **256 fichiers**,
analyse statique de **93 modules**. Le paquet contient **98 fichiers applicatifs**
comparés aux sources. Les nouveaux tests portent sur les identités, liens Mako,
dates, contrats, exclusions Associate/stages, bornes et extraits des fiches.


## Installation vérifiée

Publié sur `main`, commit applicatif `b533c15751d8519941bdb075a62b512f1f416515`, installé le
**27/09/2026 · 21:10** après sauvegarde vérifiée. Les huit premières
collectes avec le paquet installé ont réussi : **69 nouvelles offres**,
**112 requêtes**, aucune alerte historique, aucun ancien score ni suivi modifié.

Contrôle à **27/09/2026 · 21:18** : **1093 offres**, **325 pertinentes**,
**200 prioritaires**, **55/55 sources à jour**.
**641 dates de publication**, **506 fiches avec missions**, **422 avec
indications de diplôme**. Scanner actif, dashboard et API du suivi répondent ;
paquet installé comparé fichier par fichier et services programmés relancés.
Vingt sources existantes ont déjà réussi une collecte automatique après la
reprise. Les deux anomalies Goldman Sachs/Citi présentes dans la sauvegarde
d'avant installation ont disparu au passage suivant, sans changement de code.

Le dashboard a été vérifié dans le navigateur après rechargement : nouveaux
employeurs présents dans le filtre, tris de publication, fiches et liens visibles.
Les filtres ont été réinitialisés après le contrôle, sans modifier de candidature.

Observation ultérieure à **27/09/2026 · 21:22** : **54/55 sources à jour**.
Nomura professionnels a signalé une pagination incohérente à 21:19 ; reprise
automatique possible après 21:29. Les huit nouvelles sources restent à jour.
Il s'agit du portail professionnel existant, distinct du portail campus/CAPTCHA.

Tous les [contrôles GitHub du commit applicatif](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36343372166) ont réussi : Python
3.11, 3.12, 3.13 et 3.14, tests JavaScript, construction de l'image et exercice
de sauvegarde/restauration en conteneur isolé.
