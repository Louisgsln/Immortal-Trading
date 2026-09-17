# Visibilité de l’expérience — audit indépendant du lot 35

## Résultat

L’indicateur d’expérience donne une information distincte du score. Parmi les **163 offres actives à score ≥70**, **six ont un minimum reconnu de trois années** ; **136 n’ont aucun minimum chiffré reconnu**. La nouvelle indication ne modifie ni le classement, ni les exclusions, ni les scores.

La comparaison indépendante des **814 offres** avec `experience_requirement(job)` confirme les résultats attendus, sans différence et sans modification des objets Job. **10 régressions indépendantes réussissent** ; Ruff est validé.

## Méthode

Lecture de la seule table `jobs` via SQLite `mode=ro`, `query_only=ON` et transaction. Aucune table de candidatures, aucun réseau et aucune écriture en production. Le calcul de référence prend le maximum des minima reconnus par le parseur de score existant et de `minimum_experience_years` lorsque ce champ n’est pas nul. Un zéro structuré est conservé ; une valeur absente ne devient pas zéro.

[experience-audit.json](../data/discovery/lot35/experience-audit.json) contient les résultats des 814 offres, les quatre regroupements, 20 exemples avec IDs, extraits et offsets, le hash des données et la validation du helper. Les tests sont dans [test_experience_regressions.py](../tests/test_experience_regressions.py).

## Compteurs

Les catégories décrivent le **minimum reconnu**, jamais un plafond d’expérience accepté ni une décision d’éligibilité.

| Population | Total | Minimum 0–2 ans | Minimum >2 ans | Minimum non reconnu |
| --- | ---: | ---: | ---: | ---: |
| Toutes les offres | 814 | 55 | 163 | 596 |
| Offres actives | 812 | 55 | 163 | 594 |
| Actives, score ≥70 | 163 | 21 | 6 | 136 |
| Actives, score ≥55 | 250 | 25 | 29 | 196 |

## Les six offres prioritaires avec minimum supérieur à deux ans

Toutes ont un minimum reconnu de **3 ans**. Leur pertinence métier peut maintenir un score élevé alors que la composante junior vaut zéro.

| Entreprise et titre | ID local | Score |
| --- | --- | ---: |
| Société Générale — eFX Trader | `ad231b91-2f15-46f3-9e30-95a483bd45ef` | 72 |
| Macquarie — Intraday Algo Trader | `e2cc63d1-a2e4-4318-b2f7-1e8b2bbf0c1a` | 72 |
| IMC — Quantitative Trading Strategist - Equity Options | `10ac3017-ea1c-4cda-a811-26c8135ff026` | 70 |
| Flow Traders — Digital Assets Trader | `db30eab9-f62d-471e-b6c9-c99dff5c53f6` | 74 |
| Flow Traders — Digital Assets Trader | `2762ba0d-7ef3-4963-b009-ea21d7832fe1` | 74 |
| Flow Traders — Digital Assets Trader | `c11def96-a695-408a-a1a9-99f3fb5f745f` | 74 |

Les trois Flow précisent « Minimum 3+ years of professional trading experience » et « this is not an entry-level or junior role ». L’indicateur rend cette exigence visible sans réinterpréter leur score 74 comme une validation d’éligibilité junior.

## Contre-exemples nécessaires à l’interface

- **Junior ne signifie pas minimum zéro.** DRW Floor Trader, `bc7cb69d-4865-4a23-a82e-39bdc356d48e`, conserve son score **82** et ses **20/20 junior**, mais son minimum vaut `None`. La description dit « Prior trading or financial-markets experience is helpful but not required » : aucun nombre ne doit être inventé.
- **Zéro structuré ne signifie pas poste adapté.** Dix offres ont un minimum structuré de zéro ; sept restent à score nul. Crédit Agricole CIB, `08a2020e-e21e-41c4-9932-fd32597fe8af`, mentionne « 0-2 years of financial markets experience » mais porte le contrat `Internship/Trainee` : minimum zéro, exclusion de stage conservée.
- **Le champ structuré peut apporter la preuve.** Nomura GM-Global Markets, `65ffbd25-a7dd-4b17-b858-c58c71ea61d8`, conserve zéro depuis le champ structuré, cohérent avec « Experience 0-2 years of experience ». Jump Quantitative Developer, `b8409c7c-9e90-4117-9844-984037cf05dc`, conserve cinq ans depuis son minimum structuré issu du « 5+ year track record » ; le poste reste exclu.
- **Une préférence n’est pas un minimum obligatoire.** UBS ETF Capital Markets Specialist, `f69f31eb-efb3-48c2-948b-958aba2504f4`, dit « ideally 7+ years’ experience » ; le parseur existant ne retient pas ce nombre comme exigence.
- **Non reconnu ne signifie pas absent de l’annonce.** Jump Quantamental Research Analyst, `26e2a615-1c4c-4dfd-92cd-91bb072063b6`, mentionne « 3–6 years in buy/sell-side research, prop trading, ETF/index research, or corporate actions analysis », formulation non reconnue actuellement. Son indicateur reste `unspecified`, et son exclusion métier reste en place.

## Limites et validation

Une phrase qualitative telle que « this is not an entry-level or junior role », « experienced trader » ou « several years » ne fournit pas de minimum numérique. L’absence de détection doit donc être affichée comme **Minimum non reconnu**, et non « sans expérience requise ».

Une fourchette « At least 2-5+ years » donne le minimum 2. La catégorie `up_to_2` signifie que le **minimum détecté est inférieur ou égal à deux**, pas que l’employeur accepte uniquement zéro à deux années. Les préférences, bornes de fourchette et formulations reconnues restent exactement celles du parseur existant ; ce lot n’en élargit pas la couverture.

Les tests indépendants couvrent Floor Trader, la distinction entre score et minimum Flow, les séniorités sans nombre, le zéro structuré sur un stage, le minimum structuré cinq ans, une préférence UBS et la limite de lecture Jump. Chaque observation vérifie que le Job, son score et ses exclusions restent inchangés. L’admissibilité réelle reste à vérifier dans les exigences complètes de l’annonce.
