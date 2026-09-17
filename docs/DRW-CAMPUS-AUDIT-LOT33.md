# Audit indépendant DRW Campus — lot 33

## Conclusion et périmètre

Le replay hors réseau des **154 annonces DRW** de la capture du lot 32 conserve les **27 mêmes offres** après filtrage. Une seule offre doit recevoir le nouvel indice employeur junior : **Floor Trader, `8207750`**, dont le score passe de **79 à 94**. Cette correction ne concerne pas tous les programmes Graduate ni toutes les formulations de diplôme.

La base observée contient **814 offres**. Cet audit ne modifie pas la base, le collecteur, le scorer ni la configuration. Le replay de la capture et les tests utilisent des objets en mémoire ; la lecture SQLite utilise `mode=ro`, `query_only=ON` et une transaction. Aucune donnée de contact ou note de candidature n’est lue.

Preuves locales :

- [quality-audit.json](../data/discovery/lot33/quality-audit.json) : compteurs, IDs, métadonnées, extraits de description avec offsets, résultats avant/après et hashes des fichiers source.
- [parser-before.json](../data/discovery/lot33/parser-before.json) : référence des 27 offres sauvegardée par le parent avant modification.
- [test_drw_campus_regressions.py](../tests/test_drw_campus_regressions.py) : 22 cas indépendants passant par `parse_board`, puis le scorer lorsque nécessaire ; aucun appel direct au nouveau helper.

## Les cinq offres Campus retenues

La capture contient 32 annonces dont la catégorie vaut exactement `['Campus']`, dont cinq passent les filtres métier existants. Trois de ces cinq ont le contrat exact `Full-time`.

| ID externe | Offre | Contrat | Preuve de diplôme | Indice junior attendu | Effet sur le score |
| --- | --- | --- | --- | --- | --- |
| `8207750` | Floor Trader | Full-time | `have an expected graduation date between December 2026 and June 2027` | junior | **79 → 94** |
| `7957241` | Quantitative Trading Analyst | Full-time | `related field graduating between December 2026 and June 2027` | aucun nouvel indice | 96 inchangé ; le titre donne déjà 20/20 junior |
| `8014946` | Quantitative Trading Analyst | Regular | même formulation `graduating between` | aucun nouvel indice | 96 inchangé |
| `7957243` | Quantitative Trading Analyst Intern | Full-time | `expected graduation date between December 2027 and August 2028` | aucun | zéro, stage |
| `7668776` | Quantitative Trading Analyst Intern | Intern | `expected graduation date between December 2027 and June 2028` | aucun | zéro, stage |

L’offre `7957243` est le contre-exemple déterminant : un stage peut porter la métadonnée `Full-time`. Son titre contient `Intern` et sa description comprend « What to expect during the internship ». Les métadonnées Campus et Full-time, même associées à une date de diplôme, ne suffisent donc pas seules.

## Preuve positive Floor Trader

La rubrique **What you bring to the team** de `8207750` commence par un diplôme candidat :

Le candidat doit préparer un diplôme dans une discipline pertinente et prévoir de le terminer entre décembre 2026 et juin 2027.

La même annonce précise que l’expérience préalable des marchés est utile mais non requise. La catégorie Campus, le contrat Full-time et le critère candidat explicite constituent une preuve convergente de début de carrière.

La correction conserve le début publié **Summer 2027**, sans fabriquer de jour précis. La date de diplôme ne devient ni date de publication, ni date de début, ni échéance de candidature. La publication reste le 16 septembre 2026 à 22:00:49 UTC et la deadline reste inconnue. L’ajout de l’indice employeur fait uniquement passer la composante junior de 5 à 20 dans le calcul observé ; les autres composantes du score restent identiques.

## Bornes volontaires de la règle

La règle exige, pour DRW uniquement :

1. La catégorie exacte `['Campus']` et le contrat exact `Full-time`.
2. Une rubrique candidat **What you bring to the team** unique.
3. Une formulation de diplôme candidat contenant **expected graduation date between MONTH YEAR and MONTH YEAR** dans le même bloc ou la même phrase pertinente.
4. L’absence de preuve de stage dans le titre ou la partie pertinente du poste.

La variante **graduating between**, pourtant présente dans les deux offres Analyst, reste volontairement hors du périmètre de l’inférence. Leurs scores junior sont déjà corrects grâce au titre. Les rôles **Regular**, les catégories Trading/Technology et les mentions de campus ou de diplômés dans le texte général de l’entreprise ne sont pas requalifiés.

L’indice junior n’annule pas les règles de séniorité ou d’expérience : un titre Senior/VP reste filtré ; une exigence explicite de cinq années conserve un score nul. Le classement n’atteste pas de l’éligibilité personnelle du candidat ni de sa disponibilité.

## Régressions indépendantes et défaut détecté

Les tests vérifient le chemin public `parse_board` avec de petits enregistrements synthétiques, fondés sur les preuves ci-dessus : formulation Floor Trader, emphase HTML autour des dates, variante Analyst volontairement inchangée, contrats et catégories alternatifs, métadonnée Campus absente, stages marqués Full-time, séniorité et cinq années d’expérience. Ils couvrent aussi une mention de diplôme concernant d’autres étudiants et des formulations niées ou non requises.

La première exécution a révélé un défaut de portée : un titre Floor Trader et un critère de diplôme valide obtenaient l’indice junior même si une rubrique suivante disait **What to expect during the internship**. La borne d’extraction s’arrêtait juste avant ce titre et le contrôle des stages ignorait ainsi le bloc qui portait précisément la preuve de stage. Ce cas dérive de l’annonce réelle `7957243`, avec un titre synthétique sans le mot Intern pour tester la protection par la description.

Le défaut a été corrigé par l’implémenteur ; la nouvelle exécution des **22 régressions indépendantes réussit**, y compris le stage indiqué dans une rubrique après les exigences. La contre-revue confirme que la garde de stage couvre désormais le rôle jusqu’à l’introduction générale de DRW, indépendamment de la fin de la rubrique des exigences.

La mesure globale du parent confirme **une seule offre requalifiée** sur les 814 : `8207750`, avec modification de l’indice, de la séniorité calculée et du score 79 → 94. Les 26 autres offres DRW du replay et les 813 autres offres stockées restent inchangées dans cette comparaison. La réparation de l’historique et des colonnes persistées est contrôlée séparément par le parent, pas réalisée par cet audit.
