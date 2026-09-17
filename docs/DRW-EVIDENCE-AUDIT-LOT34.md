# Audit indépendant des preuves d’actifs DRW — lot 34

## Conclusion

Les **27 offres DRW** stockées comportent un passage d’entreprise qui attribue au groupe plusieurs marchés. Ces informations ne suffisent pas à qualifier chaque poste. Une simulation indépendante retirant uniquement **deux signatures textuelles exactes** de la vue destinée aux actifs et aux termes de profil modifie 25 listes d’actifs, 24 listes de termes et **9 scores totaux**. Le scorer intégré reproduit les 27 résultats projetés.

**Floor Trader `8207750`**, ID local `bc7cb69d-4865-4a23-a82e-39bdc356d48e`, passe de **94 à 82** : sa compatibilité junior reste à 20/20, mais FX/Equities/Commodities ne sont plus attribués au poste à partir de la présentation du groupe. Python reste étayé par la description. Aucun actif n’est déduit du nom de département présent dans la capture.

## Preuves et signatures

La lecture concerne les 27 offres DRW de la base de 814 offres et la capture locale DRW du lot 32. SQLite est ouvert en `mode=ro`, avec `query_only=ON` et transaction. Aucun réseau, aucune donnée de candidature, aucune écriture de production.

[quality-audit.json](../data/discovery/lot34/quality-audit.json) conserve les signatures intégrales, leurs occurrences exactes, les IDs, les extraits et les résultats avant/après. Deux formulations ont été vérifiées :

- **`headquarters_v1` — 26 occurrences identiques** : paragraphe commençant par « Headquartered in Chicago with offices throughout the U.S., Canada, Europe, and Asia », citant Fixed Income, ETFs, Equities, FX, Commodities et Energy, puis se terminant par « real estate, venture capital and cryptoassets. »
- **`prediction_v1` — 1 occurrence** : première phrase de Prediction Markets Trader `7520816`, commençant par « DRW is a major Chicago-based proprietary trading firm founded in 1992 by Don Wilson », et listant les marchés du groupe jusqu’à « FX, and cryptocurrency. »

Le premier paragraphe débute à l’offset 316 dans **21 descriptions**, avant le rôle. Dans les six autres annonces, les positions sont : 0 pour la seconde signature ; 2210 pour deux Analyst ; 3555 et 3576 pour les deux stages ; 2446 pour Floor Trader. **Tronquer toute la description après l’introduction DRW supprimerait donc des missions et exigences réelles dans de nombreuses offres.**

## Effet mesuré, limité aux actifs et au profil

| Élément | Offres modifiées |
| --- | ---: |
| Liste d’actifs | 25 |
| Liste de termes de profil | 24 |
| Points d’actifs | 12 |
| Points de profil | 22 |
| Score total | 9 |

Les 15 offres DRW déjà exclues restent à zéro. Les offres DRW à score ≥70 passent de 12 à 11 ; celles à score ≥55 restent au nombre de 12. Les points junior, Front Office, début, les exclusions et le texte complet sont conservés. Une explication de filtrage est ajoutée aux **27 offres**, y compris lorsque le score total ne change pas : le nombre d’événements de recalcul peut donc dépasser neuf.

| ID externe | Offre | Score avant → après |
| --- | --- | ---: |
| `8207750` | Floor Trader | **94 → 82** |
| `8014946`, `7957241` | Quantitative Trading Analyst | 96 → 84 chacun |
| `8138564` | Quantitative Trading Analyst - GD1 | 88 → 76 |
| `7912433` | Equity Dispersion Trader | 77 → 75 |
| `8094311` | Data Analyst - Global Markets and Equities | 76 → 74 |
| `8079361` | Equity Index Voice Trader | 70 → 68 |
| `8079147` | US Equity Index Options Trader | 73 → 71 |
| `8127674` | Associate Trader | 72 → 70 |

Ces résultats sont des recalculs en mémoire lors de l’audit. L’aperçu global du parent confirme 814 offres évaluées, 27 changements tous limités à DRW et neuf scores totaux modifiés : les offres actives à score ≥70 passent de **164 à 163**, celles à score ≥55 restent à **250**. L’application et les contrôles d’historique relèvent de la validation menée par le parent.

## Preuves réelles conservées

- **Associate Trader `8127674`** conserve EQUITIES : « Conducting in depth research on single name equities » se trouve après le paragraphe d’entreprise.
- **Quantitative Trader - Futures `7730933`** conserve notamment FX, rates et commodities grâce aux missions de stratégies futures « across global markets (rates, FX, commodities, equities) ». Son exclusion pour expérience reste intacte.
- **Quantitative Trading Analyst `7929846`** conserve FX dans les qualifications : « including equities, rates, credit and FX ».
- **Trading Application Specialist `8119503`** répète explicitement les marchés dans le périmètre de ses projets ; ces preuves restent présentes, ainsi que son exclusion métier.
- **Prediction Markets Trader `7520816`** conserve OPTIONS grâce à « closely related domains (options, binary events, sports/event betting) ». FX et les dérivés ne sont plus retenus depuis la première phrase d’entreprise ; son score reste 77, notamment parce que les autres termes de profil atteignent déjà le plafond.

## Bornes et régressions

La règle est réservée à l’identité DRW vérifiée : entreprise et nom normalisé DRW, source `drw`, type `official`. Elle enlève les deux passages reconnus de la seule vue de calcul des actifs et termes de profil. Le titre reste inclus ; le texte complet reste disponible à l’affichage et aux règles de dates, séniorité, Front Office et exclusions. Une phrase proche mais non reconnue n’est pas supprimée.

**18 tests indépendants** dans [test_drw_evidence_regressions.py](../tests/test_drw_evidence_regressions.py) réussissent en passant par `score_job`. Ils couvrent les deux signatures, les preuves métier avant/après, les actifs dans le titre, les identités hors périmètre, la conservation des textes et des règles d’exclusion/date/Front Office. Ruff est validé. Une comparaison indépendante confirme également les résultats projetés pour les **27 offres réelles**.

Cette correction ne garantit pas que toute autre formulation restante est spécifique au rôle. Les passages génériques inconnus, les autres employeurs et les autres composantes du barème restent hors périmètre. `UNKNOWN` signifie qu’aucun terme d’actif n’est reconnu hors des deux passages retirés ; cela ne signifie pas que le poste ne négocie aucun actif.
