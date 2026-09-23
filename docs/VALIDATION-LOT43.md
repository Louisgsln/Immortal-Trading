# Lot 43 — Actualisation Workday et grades seniors explicites

Travaux des **23–24 septembre 2026** (Europe/Paris). Actualisation bornée de
Barclays, Deutsche Bank, Morgan Stanley et Citi, suivie d’une correction ciblée
des grades employeur. Le périmètre reste la recherche `trading` configurée ;
aucun filtre, budget, cache ou barème global n’est modifié.

## Collecte et revue

| Source | Résultats de recherche | Fiches retenues | Requêtes | Nouvelles | Mises à jour |
| --- | ---: | ---: | ---: | ---: | ---: |
| Barclays | 102 | 16 | 23 | 1 | 0 |
| Deutsche Bank | 320 | 26 | 43 | 7 | 4 |
| Morgan Stanley | 306 | 17 | 34 | 4 | 2 |
| Citi | 1 174 | 51 | 111 | 2 | 2 |
| **Total** | **1 902** | **110** | **211** | **14** | **8** |

Les totaux concernent la recherche publique, pas l’ensemble des postes des
employeurs. Les quatre sources réussissent, avec robots compris, deux secondes
entre requêtes par hôte et aucun retry. Captures commencées le 23 septembre à
21:43:48 UTC, terminées à 21:47:31 UTC ; import terminé à 21:59:04 UTC.

Réponses CXS et collections archivées avec URL, corps de recherche, horodatage,
taille et SHA-256. Chaque rejeu vérifie les empreintes, la configuration et un
âge inférieur à trente minutes depuis le début de collecte. Les réponses brutes
repassent dans le collecteur corrigé, sans réseau ; seul l’ajout d’un indice
senior est accepté par rapport aux collections initiales. Les compteurs des
rejeux indiquent donc zéro requête, distinct des 211 requêtes de capture.

La revue des 22 changements est réalisée par l’agent principal. Les quatre
modifications de contenu antérieur sont :

- Morgan Stanley `JR043965` : Analyst devient Analyst or Associate, qualification
  de master et rémunération Associate ajoutées ; score zéro conservé.
- Morgan Stanley `JR042373` : niveau Excel désormais avancé ; score 63 conservé.
- Citi `26992518` : années de diplôme 2027/2028 ; stage toujours exclu.
- Citi `26987507` : date de fin de publication annoncée déplacée au 4 octobre ;
  ce texte n’est pas transformé en échéance de candidature confirmée.

Les quatre autres mises à jour apportent l’indice senior décrit ci-dessous.
Les dates Workday de publication ne deviennent pas des dates de prise de poste.

## Correction de seniorité

Le collecteur reconnaît trois formes précisément auditées :

- **Deutsche Bank** : paragraphe autonome `Corporate Title` avec Vice President,
  Director ou Managing Director. Analyst et Associate ne sont pas promus juniors.
  Des grades contradictoires arrêtent la collecte avant validation du snapshot.
- **Morgan Stanley** : suffixe de titre `- ED` concordant avec le grade Executive
  Director dans le champ publié `jobPostingId`. Une URL ou l’acronyme seul ne suffit pas.
- **Citi** : paragraphe désignant directement le Director de l’EMEA Cash Electronic
  Execution Desk comme rôle senior. Aucune règle générale sur le mot Director.

Source et employeur doivent correspondre. Citations HTML, scripts, modèles et
éléments `hidden` sont ignorés. Aucun nombre d’années d’expérience n’est déduit
du grade. L’exclusion senior existante reste responsable du score zéro.

| Référence | État | Score sans nouvel indice → après |
| --- | --- | ---: |
| DB `R0425798`, Quantitative Trading Engineer | Existante | 0 → 0 |
| DB `R0432497`, Emerging Market Corporate Debt Structured Credit Trader | Existante | 71 → 0 |
| DB `R0439897`, Credit Risk Officer, Energy Trading | Existante | 69 → 0 |
| DB `R0441591`, Energy trading Valuation Risk Manager | Existante | 71 → 0 |
| DB `R0448865`, Fixed Income Trader | Nouvelle | 69 → 0 |
| MS `PT-JR043325`, Algorithmic Trading Engineer - ED | Nouvelle | 62 → 0 |
| Citi `26985573`, Electronic Execution Sales Trader | Nouvelle | 77 → 0 |

Le simple recalcul des 820 anciens JSON n’a aucun effet : les nouveaux indices
proviennent de la collecte. Sept fiches entrantes reçoivent un indice ; six
quittent le groupe pertinent par rapport à l’aperçu sans correction, dont trois
fiches déjà présentes dans la base. Aucun minimum professionnel n’est inventé.

## Préservation et résultat

Sauvegarde `data/backups/lot43-before-workday.zip`, restauration des onze tables
et répétition sur une base distincte avant import. Résultats identiques :
**14 ajouts, 8 modifications, aucune fermeture, alerte ni source en échec**.

- 820 suivis existants conservés intégralement ; 14 suivis `New` créés.
- 96 offres existantes observées ; 724 anciennes lignes strictement inchangées.
- 29 anciennes offres actives absentes de ce périmètre restent conservées, avec
  leur ancienne date d’observation, notamment plusieurs programmes campus 2027.
- 110 fiches importées comparées aux données normalisées des captures ; les
  22 événements d’historique concordent exactement avec l’aperçu accepté.
- Historiques antérieurs, candidatures, alertes et schéma préservés. Vingt états
  de source non concernés inchangés. Intégrité SQLite et relations vérifiées.
- Deuxième aperçu : zéro changement et onze tables préservées. Les 834 lignes
  CSV et fiches HTML concordent avec SQLite, scores et expérience compris.

Base finale : **834 offres, 832 actives, 246 pertinentes et 166 prioritaires**.
Parmi les actives : **71 minima reconnus 0–2 ans, 187 >2 ans, 574 non reconnus**.
Neuf sources sont fraîches et quinze anciennes : le diagnostic global reste
critique. Une source fraîche ne confirme pas la présence actuelle de ses offres
historiques absentes de la recherche.

## Vérifications

**2 652 tests réussis**, dont 48 nouveaux cas, sur le paquet non éditable sous
Windows Python 3.14 ; couverture **96 %**. Ruff et formatage passent sur 181
fichiers, mypy sur 69 fichiers incluant quatre scripts.

Edge valide l’export statique et le serveur éditable local : compteurs et filtres,
quatre fiches seniors à zéro, nouveau GEM Trader Analyst DB à 90, minimum IMC
et preuves Jump/Crédit Agricole/Macquarie conservés. Affichage à 390 pixels sans
débordement, vingt variantes de preuves contrôlées, aucune erreur JavaScript.

La CI du commit `7b92cb0ee4bb2193e94f1883285c30451012ee32` réussit dans
[le run du lot 43](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35925769334).
Python **3.11 à 3.14** passent chacun les **2 652 tests**, avec **96 % de
couverture**. Build Docker, ENTRYPOINT et reprise synthétique réussis sous
UID **10001**, réseau coupé, avec **onze tables restaurées identiques** ; le
volume de test est nettoyé. Les cinq journaux CI sont conservés localement.

## Prochaines étapes et limites observées

Les nouvelles fiches DB `R0452740` et `R0450097` exposent respectivement un
minimum écrit `three (3) years` et une fourchette `1-4 years of prior work
experience`. Le parseur actuel affiche un minimum non reconnu, avec des scores
75 et 78. Ce sont des lacunes à corriger par une extension bornée et mesurée ;
« non reconnu » ne signifie pas absence d’exigence.

DB Risk and Trading AS et les Trading Assistant MS combinent trading et support.
Leurs scores ne remplacent pas une revue des missions. Poursuivre cet audit sans
lever globalement les exclusions, puis actualiser les quinze autres sources.
Supervision prolongée et copie distante des sauvegardes restent à préparer sur
l’hôte Docker validé. Aucun watcher permanent ni candidature n’a été lancé.

Les preuves locales restent dans `data/discovery/lot43/`, hors Git : captures,
aperçus avant/après correction, revue, mesures, sauvegarde restaurée, contrôles
de préservation, tests, captures Edge et journaux CI. Code, tests et bilan sont
versionnés ; la base et les données personnelles ne sont pas publiées.
