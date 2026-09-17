# Audit qualité Greenhouse — lot 32

## Résultat

Sur les **88 offres déjà conservées** des cinq employeurs ciblés, aucun titre Graduate n’est exclu à tort. Les **22 titres Graduate/Junior/Intern/Analyst** comprennent **12 scores nuls** : 11 stages explicitement exclus par les règles du projet et un Research Analyst demandant 3–6 ans d’expérience.

L’examen séparé de la nouvelle capture DRW révèle une **sous-pondération junior démontrée** : Floor Trader, identifiant externe `8207750`, est une offre Campus à temps plein visant des diplômés 2026–2027, mais reçoit seulement 5/20 pour la compatibilité junior. Son score actuel de **79** la maintient néanmoins parmi les offres prioritaires. Une correction étroite est proposée ci-dessous ; aucun code, réglage ni score stocké n’a été changé par cet audit.

## Périmètre et méthode

Photographie locale du **17 septembre 2026 à 06:55:09 UTC**, avant intégration de la nouvelle offre : 813 offres dans la base, dont 88 pour les sources `imc`, `drw`, `flow_traders`, `jump_trading` et `xtx_markets`. La base est ouverte via SQLite `mode=ro`, `query_only=ON` et transaction de lecture. Aucune table de candidatures n’est interrogée.

Les conclusions reposent sur les descriptions conservées, les exclusions, les indices structurés de l’employeur et les règles de score locales. Aucun appel réseau. La nouvelle offre est examinée depuis `data/discovery/lot32/capture-live/drw.json`, capturé séparément par le parent.

La preuve [quality-audit.json](../data/discovery/lot32/quality-audit.json) contient les 88 IDs locaux, URLs, scores, exclusions, minima détectés, hash des descriptions et extraits avec offsets. La rubrique `new_capture_review` conserve séparément les preuves de l’offre nouvelle et le hash de sa capture. Les compteurs ci-dessous ne comprennent pas cette offre.

| Source | Offres actives | Score nul | Titres ciblés | Titres ciblés à zéro | Score ≥70 |
| --- | ---: | ---: | ---: | ---: | ---: |
| IMC | 26 | 9 | 6 | 4 | 12 |
| DRW | 26 | 15 | 7 | 2 | 11 |
| Flow Traders | 10 | 4 | 4 | 1 | 6 |
| Jump Trading | 25 | 11 | 5 | 5 | 6 |
| XTX Markets | 1 | 0 | 0 | 0 | 0 |
| **Total** | **88** | **39** | **22** | **12** | **35** |

## Exclusions correctes et offres junior conservées

Les 11 stages portent tous `Intern` dans le titre : quatre IMC, deux DRW, un Flow et quatre Jump. Exemple révélateur : DRW `6d35be5e-95f1-4466-b5f3-9c660c7d1aad`, **Quantitative Trading Analyst Intern**, indique `Full-time` dans ses métadonnées, mais la description dit « What to expect during the internship ». L’exclusion par le titre évite donc de transformer un stage à temps plein en poste permanent.

Les cinq titres Graduate IMC/Flow reçoivent 76 à 86, sans exclusion. DRW Data Analyst, `7c29181c-c199-4b0a-9db1-b240442c0bf2`, reçoit 76 et 20/20 junior, cohérent avec « New Grads are welcome! ». Jump Campus Quantitative Trader Full-Time, `9a25b5a6-15e5-47bd-92a2-ae04928f2629`, reçoit 74 avec un indice junior explicite ; les mentions de programmes universitaires ne sont pas interprétées comme stages.

Les fortes exigences restent distinctes : DRW Quantitative Trader Futures, `a52ad6ee-18a6-4c7a-a686-f8405b3c0639`, demande « 7+ years of experience in systematic trading » et reçoit zéro. Jump Deep Learning Researcher, `1fd9d019-2192-4426-8f9e-3640e8500e8c`, demande « At least 5+ years of experience in developing DL systems » et reçoit également zéro. Ces exclusions correspondent aux preuves conservées.

## Motifs à réexaminer sans lever l’exclusion dans ce lot

### Jump : Research Analyst n’est pas synonyme de recherche isolée du trading

`26e2a615-1c4c-4dfd-92cd-91bb072063b6`, **Quantamental Research Analyst | Trading Team**, reçoit zéro uniquement à cause de `research analyst`. Pourtant, la mission dit « Collaborate with quantitative traders globally in performing in depth research on ETF pricing and trading strategy ». Le filtre lexical masque donc ici une activité de recherche intégrée au trading, et pas seulement de la recherche pure.

La même annonce demande « 3–6 years in buy/sell-side research, prop trading, ETF/index research, or corporate actions analysis », formulation non extraite par le parseur actuel. Ce n’est donc **pas une offre junior injustement bloquée démontrée**. Lever simplement `research analyst` sans traiter cette exigence créerait une amélioration trompeuse du classement. Conserver le cas comme preuve pour une correction future conjointe de la qualification métier et de l’expérience.

### Deux postes techniques mêlent trading et opérations

- IMC **Trading Engineer - Execution**, `f04aa0df-f736-4e73-8359-fb703e06e810` : zéro pour `software role without embedded trading evidence`, alors que la mission décrit des « systems that sit directly in the critical path of live trading ». La fourchette `2-5+ years` est correctement réduite à 2. La description insiste aussi sur le support opérationnel, la connectivité et les systèmes : le rattachement au trading est réel, mais l’adéquation au périmètre Front Office visé nécessite une décision explicite.
- Jump **Quantitative Developer | Trading Team**, `1c24a2a1-a702-4131-a63c-d75f1aed9c8c` : même exclusion, mais la description se présente comme « a hybrid development and research and trading operations position ». `At least 2-5+ years` est correctement lu comme 2. Le rôle mélange développement, surveillance et assistance de production ; la présence de trading dans la description ne suffit pas à démontrer une erreur d’exclusion selon les critères conservateurs actuels.

Ces cas justifient une revue ciblée du périmètre métier, pas l’ajout global de `live trading` comme passe-droit. Le rôle XTX déjà validé, `34f9ad24-1ae7-4463-8b71-a2175dadd5d8`, reste admis grâce à l’indice vérifié `trading_technology`, avec un score de 65 sans hypothèse de séniorité junior.

## Ambiguïtés d’expérience et portée du score

IMC Commodities Volatility Trader, `fdb0d33e-70ad-4f8a-b1c5-915131ace5c2`, contient « 3+ years’ experience in Commodities Options markets highly preferred, other asset classes ... ». Le parseur retient 3 ; la préférence peut viser le marché Commodities plutôt que supprimer toute exigence d’expérience. Ce texte ne justifie pas une correction automatique de portée.

Trois Flow Digital Assets Trader (`db30eab9-f62d-471e-b6c9-c99dff5c53f6`, `2762ba0d-7ef3-4963-b009-ea21d7832fe1`, `c11def96-a695-408a-a1a9-99f3fb5f745f`) indiquent « Minimum 3+ years of professional trading experience » et « this is not an entry-level or junior role ». L’expérience est bien détectée et la composante junior vaut zéro, mais le score total reste 74. Deux autres postes demandant trois ans restent à 70 : DRW Equity Index Voice Trader et IMC Quantitative Trading Strategist. **Un score ≥70 mesure la pertinence globale, pas une certification d’éligibilité junior.** Il s’agit du comportement actuel du barème, pas d’une omission du minimum dans ces cinq cas.

## Nouvelle capture : DRW Floor Trader, `8207750`

[Annonce dans la capture officielle](https://job-boards.greenhouse.io/drweng/jobs/8207750), Chicago, département **FICC Options Trading - Liquidity Providing**.

- Contrat : `Full-time` ; catégorie employeur : `Campus`.
- Début cible : `Summer 2027`, conservé sans inventer un jour précis.
- Diplôme : « expected graduation date between December 2026 and June 2027 ».
- Expérience : « Prior trading or financial-markets experience is helpful but not required » ; aucun minimum chiffré détecté ni structuré.
- Activité : répartition du temps « between the Cboe trading floor and DRW’s trading desk ».
- Première publication et mise à jour : `2026-09-16T18:00:49-04:00`, soit `2026-09-16T22:00:49Z` ; deadline absente.

Le replay local du parseur et du scorer donne **79** : trading 30, junior 5, début 15, Front Office 15, actifs 10 et adéquation au profil 4 ; aucune exclusion. `seniority_hint` reste vide parce que le titre Floor Trader ne porte pas de mot campus/graduate. Le diplôme attendu et la catégorie employeur prouvent pourtant la cible début de carrière.

**Correction étroite proposée pour la suite :** permettre à l’adaptateur DRW de fournir l’indice junior uniquement avec une combinaison validée de catégorie `Campus`, contrat `Full-time`, formulation explicite de diplôme attendu et absence de stage dans le titre/description pertinente. Vérifier les stages DRW marqués `Full-time` comme contre-exemples. Avec le seul indice junior changé, le barème donnerait 94 ; ce chiffre est une simulation arithmétique, pas un score appliqué.

Les actifs FX/Equities/Commodities et le mot-clé FX proviennent ici du texte général DRW ; ils ne certifient pas la spécialisation exacte du desk. La date de diplôme attendue ne prouve pas non plus la disponibilité personnelle du candidat. Ces limites n’empêchent pas l’import de l’offre avec son score actuel et ses preuves visibles.
