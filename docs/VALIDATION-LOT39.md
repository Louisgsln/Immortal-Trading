# Lot 39 — Exigences d’expérience formulées avec « years in »

Travaux du **17 septembre 2026**, avec trois sous-agents : implémentation,
régressions et revue d’impact indépendantes, audit de deux cas ambigus.
L’agent principal intègre, mesure, sauvegarde et vérifie les résultats.

## Problème traité

Le parseur reconnaissait `3+ years of experience`, mais certaines exigences telles
que `3–6 years in buy/sell-side research` et `3+ years in options trading`
restaient absentes du minimum affiché. L’[audit du lot 38](EXPERIENCE-IN-AUDIT-LOT38.md)
a identifié sept qualifications professionnelles certaines à couvrir.

Le helper `candidate_in_experience_years` étend la reconnaissance aux formes
numériques `N–M years in` et `N+ years in`, dans un contexte de qualification
obligatoire et pour les domaines professionnels couverts par les preuves et tests.
Il conserve la borne basse d’une fourchette et le maximum des exigences reconnues
pour calculer l’indicateur d’expérience.

La préférence portant seulement sur un domaine, comme `ideally supporting
high-performance systems`, est distinguée d’une durée seulement souhaitée.
Une rubrique `Preferred:` dans la phrase suivante ne rend pas facultative
l’exigence précédente. Les durées contractuelles, maxima, négations, ancienneté
d’entreprise et alternatives académiques sont écartés dans les cas pris en charge.

Les formes `track record`, les exigences imbriquées indicatives et les domaines
inconnus restent hors de cette extension conservatrice. Le minimum structuré
préexistant n’est pas réécrit. L’[audit des cas ambigus](AMBIGUOUS-EXPERIENCE-LOT39.md)
documente l’origine de la valeur Jump et le traitement restant à définir.

## Mesure sur les 814 offres

**Sept indicateurs** passent de « minimum non reconnu » à une valeur explicite.
Huit listes de minima textuels changent : le huitième cas, Citi, ajoute cinq ans
dans une spécialité sans abaisser son minimum global déjà reconnu de dix ans.

| Offres | Minimum affiché après correction | Effet sur l’explication du score |
| --- | ---: | --- |
| Optiver — SSO Floor Trader, quatre annonces | 3 ans | Motif d’exigence supérieure à deux ans ajouté ; composante junior déjà nulle, score 66 conservé. |
| IMC — Trading Engineer - Strategy | 3 ans | Composante junior 5→0 ; exclusion métier et score nul conservés. |
| Jump — Quantamental Research Analyst | 3 ans | Composante junior 20→0 ; exclusion Research Analyst et score nul conservés. |
| UBS — APAC Algo Trading Low Latency C++ Developer | 7 ans | Composante junior 5→0 et exclusion d’expérience ≥5 ans ajoutée ; score nul conservé. |

Les **sept décompositions** de score changent, mais **aucun total**. Le classement
reste à **812 offres actives, 240 pertinentes et 161 prioritaires**.

| Catégorie d’expérience, offres actives | Avant | Après |
| --- | ---: | ---: |
| Minimum 0–2 ans | 71 | 71 |
| Minimum >2 ans | 178 | 185 |
| Minimum non reconnu | 563 | 556 |

Les deux durées contractuelles Crédit Agricole et les cas ambigus Jump/Jane Street
ne sont pas réinterprétés. Les offres prioritaires et leurs minima restent identiques.

## Validation

**2 342 tests réussis** sur le paquet installé non éditable sous Windows
Python 3.14, avec **96 % de couverture**. Les 113 nouveaux tests incluent
46 régressions indépendantes. Ruff et format passent sur 168 fichiers ; mypy
sur 67 fichiers, dont quatre scripts. La revue indépendante a fait corriger
trois faux positifs : ancienneté de `The firm`/`The team` et durée `not needed`.

Une deuxième revue a rejoué les 814 offres et vérifié les huit changements de
parseur, sept indicateurs, sept décompositions et zéro total modifié. Elle a
comparé les champs source et les onze tables à la référence initiale. L’impact
approuvé a pour SHA-256
`33080eb3e70b7f1588e11ede51df114bf467e59eaee95bb20ef4dd26c3ca7225`.

Sauvegarde créée : `data/backups/lot39-before-experience-in.zip`. Elle a été
restaurée dans une base distincte, puis le recalcul y a été répété avant application
à la base active. **807 lignes d’offres restent identiques**, sept versions et sept
entrées d’historique de score sont ajoutées ; **huit autres tables sont identiques**.
Contrats, descriptions, dates de collecte, alertes et suivi des candidatures sont
préservés. Un second recalcul ne produit aucun changement.

Les 814 lignes CSV et les 814 fiches HTML correspondent aux scores de la base ;
les minima HTML correspondent au parseur corrigé. Les parcours Edge de l’export
et du serveur local vérifient les trois catégories d’expérience, les seuils 55/70,
les quatre offres Optiver à 66 avec minimum trois ans, UBS à zéro avec sept ans et
le motif d’exclusion, et DRW Floor Trader à 82 avec minimum non reconnu.
Aucune erreur JavaScript ni écriture de candidature. Le premier essai du serveur
a précédé la fin de son démarrage ; après réponse HTTP 200, le parcours complet
a été rejoué avec succès.

La CI du commit `93185884e28f7cf9b20b582e7e272c9c1f2ffa5c` est réussie :
[exécution du lot 39](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35208577959).
Les quatre versions Python **3.11 à 3.14** passent chacune les **2 342 tests**,
avec 96 % de couverture. Le build Docker, l’entrée de commande et la reprise
réussissent : UID 10001, réseau coupé, **onze tables restaurées identiques**.
Les rapports sont conservés par la CI et les logs copiés dans les preuves locales.
WSL reste à activer sur le poste Windows pour l’exploitation Docker locale ;
ce lot valide le conteneur Linux en CI.

Les preuves locales sont conservées dans `data/discovery/lot39/`, hors Git :
snapshots initiaux, audit des cas ambigus, impact et revue indépendante,
répétition/restauration, application, recalcul sans effet, résultats pytest/JUnit,
exports vérifiés, parcours navigateur et captures. Les scripts de mesure,
de recalcul et de vérification sont également conservés. Le dépôt public
contient le code, les tests et ce bilan.
