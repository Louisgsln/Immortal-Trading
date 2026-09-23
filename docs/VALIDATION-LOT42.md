# Lot 42 — Actualisation Greenhouse et continuité des exigences IMC

Travaux du **23 septembre 2026**, après validation de Docker local sous WSL 2.
Ce lot remet à jour cinq sources publiques avec un aperçu et une répétition
sur sauvegarde avant import. Il ne démarre pas de watcher permanent.

## Catalogues et changements examinés

| Source | Catalogue public | Offres retenues | Nouvelles | Descriptions modifiées |
| --- | ---: | ---: | ---: | ---: |
| IMC | 173 | 25 | 1 | 2 |
| DRW | 168 | 28 | 2 | 0 |
| Flow Traders | 46 | 11 | 2 | 0 |
| Jump Trading | 113 | 25 | 1 | 0 |
| XTX Markets | 9 | 1 | 0 | 0 |
| **Total** | **509** | **90** | **6** | **2** |

Six requêtes publiques réussies, robots compris, avec deux secondes entre
requêtes et aucun retry interne. Captures horodatées entre 21:25:47 et 21:25:55 UTC,
archivées avec URL, taille et SHA-256. Aperçu et imports réutilisent ces réponses
sans autre requête ; empreintes, configuration et âge inférieur à trente minutes
sont contrôlés avant chaque rejeu. Les compteurs réseau des rejeux valent donc zéro.

## Revue des nouvelles offres

Les scores ci-dessous sont ceux des règles actuelles. Ils ne garantissent ni
l’éligibilité du candidat, ni une prise de poste en 2027.

| Offre et référence | Lieu | Score | Point à vérifier |
| --- | --- | ---: | --- |
| [IMC Quantitative Trader — 4983696101](https://job-boards.eu.greenhouse.io/imc/jobs/4983696101) | Mumbai | 68 | Trois ans au moins à gérer un portefeuille d’options ; minimum reconnu dans le texte. |
| [DRW Quant Researcher - Compute Markets — 7996648](https://job-boards.greenhouse.io/drweng/jobs/7996648) | Londres | 0 | Doctorat ou master ; missions de valorisation de capacité de calcul. L’abréviation du titre n’est pas classée Trading par le barème actuel : audit métier à poursuivre. |
| [DRW Trader — 8210375](https://job-boards.greenhouse.io/drweng/jobs/8210375) | Singapour | 65 | La description nomme un Junior Trader et rend l’expérience préalable facultative ; titre générique et catégorie Regular, sans indice campus. Début affiché Immediate. |
| [Flow Traders Delta One Trader — 7708220](https://job-boards.greenhouse.io/flowtraders/jobs/7708220) | Hong Kong | 76 | Trois ans minimum reconnus. Champ de début 1er juin 2026, déjà passé : ne pas en déduire un recrutement 2027. |
| [Flow Traders Trading Systems Engineers — 8195974](https://job-boards.greenhouse.io/flowtraders/jobs/8195974) | Amsterdam | 0 | Infrastructure Linux/cloud et astreintes ; exclusion logicielle conservée. Durée typique de cinq ans non convertie en minimum obligatoire. |
| [Jump Campus Quantitative Researcher PhD/Postdoc — 8209424](https://www.jumptrading.com/hr/job?gh_jid=8209424) | New York | 86 | Doctorat en cours demandé ; le score campus ne constitue pas un matching de diplôme. Aucune date de début publiée reconnue. |

Cinq offres actives connues ne figurent plus parmi les résultats retenus :
IMC `4814983101` et `4847624101`, DRW `8138564`, Flow `8035201`, Jump `7767735`.
Leur absence ne prouve pas une clôture : ces sources sont partielles, aucune
fermeture n’est déduite et leurs anciennes dates d’observation sont conservées.
La preuve Jump de deux ans de la référence absente `7767735` reste intacte.

## Changement de rubrique IMC

La description Trading Engineer - Strategy `4439286101` remplace `What You Bring`
par `Your Skills & Experience`. La même exigence de trois ans en site reliability
reste publiée. Sans correction, ce changement de titre de rubrique faisait
disparaître le minimum reconnu et passer la composante junior de zéro à cinq,
bien que l’exclusion métier conserve un score total nul.

Le helper `in_experience` accepte désormais `&` dans cette rubrique déjà reconnue
avec `and`. Onze tests couvrent les trois titres de rubrique, la remontée du
minimum jusqu’au score et au filtre, ainsi que les préférences, alternatives,
contrats, rubriques d’entreprise, activités inconnues et fourchettes inversées.

Comparaison avant/après : **aucun effet sur les 814 fiches existantes** et une
seule extraction rétablie parmi les 90 offres entrantes. Les deux descriptions
IMC actualisées conservent finalement leurs scores et décompositions précédents.
Une troisième fiche IMC, `4840228101`, change uniquement de balisage et d’espaces
HTML : texte normalisé et score identiques, aucun événement métier supplémentaire.

## Réponse du serveur de consultation sous Windows

La première suite complète et son rejeu ciblé ont reproduit des erreurs
`WinError 10053` sur des requêtes avec corps refusées par le serveur en lecture
seule. Fermer une connexion avec des octets non lus pouvait empêcher le client
de recevoir la réponse 405.

Le serveur consomme désormais les petits corps explicitement délimités, avec
une limite de **8 192 octets** et un budget total de **250 ms**, avant le refus.
Les en-têtes ambigus ou encodés par transfert ne déclenchent aucune lecture.
Les cinq méthodes restent refusées ; aucun point d’écriture n’est ajouté.
Les tests exercent aussi un corps à la limite et un envoi incomplet.

## Application et validation finale

L’aperçu final examiné porte le SHA-256
`670e0736af383d863c77349c2a5a2b9eb047bb566b595e9ae0c1e48cc2dc7c73`.
Sauvegarde vérifiée `data/backups/lot42-before-greenhouse.zip`, restauration dans
une base distincte puis répétition : les mêmes six ajouts et deux mises à jour
sont obtenus lors de l’import réel, sans échec ni alerte.

- **814 candidatures existantes intégralement préservées** ; six suivis `New`
  créés pour les nouvelles offres, sans candidature envoyée.
- **Tous les scores et décompositions des 814 offres antérieures restent
  identiques**. 84 offres reçoivent une nouvelle observation, dont deux avec
  changement de texte et une avec changement de balisage seulement.
- **730 anciennes lignes d’offres restent strictement identiques**, y compris
  les cinq absentes. Les 19 autres états de source restent inchangés.
- Historiques antérieurs conservés ; huit versions et scores, six associations
  de source et un scan ajoutés. Alertes, historiques d’alertes/candidatures et
  schéma inchangés. Intégrité SQLite et relations vérifiées.
- Après import, le rejeu d’aperçu propose **zéro changement** et conserve les
  onze tables. Les **820 lignes CSV et fiches HTML** concordent avec la base.

Résultat : **820 offres, 818 actives, 243 pertinentes et 162 prioritaires**.
Les catégories d’expérience des actives sont **71 minima 0–2 ans, 187 >2 ans
et 560 non reconnus**. **Cinq sources sont fraîches ; dix-neuf restent anciennes**,
donc le diagnostic de santé global reste critique. Le succès de cette collecte
ne certifie pas que les offres absentes sont toujours publiées.

**2 604 tests réussis**, dont 17 cas supplémentaires, sur le paquet installé
non éditable sous Windows Python 3.14, avec **96 % de couverture**. Le premier
passage et le rejeu ciblé avaient échoué sur les refus HTTP décrits plus haut ;
le passage complet après correction est réussi. Ruff et formatage passent sur
180 fichiers, mypy sur 69 fichiers dont quatre scripts.

Edge valide l’export HTML et le serveur local : compteurs, trois catégories
d’expérience, six nouveaux liens présents, minimum IMC de trois ans dans le
détail, preuves Jump/Crédit Agricole/Macquarie préservées. Les deux surfaces
passent à 390 pixels sans débordement horizontal, avec captures conservées.
Vingt variantes de preuves mal formées ou contenant du HTML sont vérifiées ;
aucune erreur JavaScript ni injection exécutée.

La [CI du lot 42](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35923490721)
réussit pour le commit `3a5ab1c58511e711abb51b32eea45b890ba3027e`.
Les versions Python **3.11 à 3.14** passent chacune les **2 604 tests**, avec
**96 % de couverture**. Le build Docker, l’ENTRYPOINT et le scénario de reprise
réussissent sous UID **10001**, réseau coupé, avec **onze tables restaurées
identiques**. Les cinq logs sont conservés dans les preuves locales.

## Preuves locales

`data/discovery/lot42/` conserve les empreintes initiales, captures publiques,
aperçus avant/après correction, revue des huit descriptions, mesure du helper,
revue acceptée, répétition et contrôles de préservation. Les fichiers de données
restent hors Git. Le code du helper et les régressions sont versionnés.
