# Qualifications « years in » — audit indépendant du lot 38

## Conclusion

Le corpus de **814 offres** contient **15 occurrences dans 15 offres** de la forme numérique `N years in`, `N–M years in`, `N+ years in` ou `N+ year track record`. Huit formulations décrivent clairement une durée demandée au candidat ; deux nécessitent une décision sémantique distincte ; deux portent uniquement sur la durée du contrat ; trois offres ont déjà un minimum textuel reconnu ailleurs.

**Aucune correction de production n’est réalisée par cet audit.** Fournir les huit minima clairs à des copies en mémoire ne change aucun score total : quatre offres Optiver ont déjà une composante junior nulle et les quatre autres offres restent exclues. Cela pourrait néanmoins corriger l’explication du score, la composante junior de trois offres exclues et sept indicateurs d’expérience aujourd’hui non reconnus. Le huitième, Jump Quantitative Developer à deux ans, possède déjà un minimum structuré de deux ans.

## Méthode et limites

- SQLite ouverte avec `mode=ro`, `query_only=ON` et transaction de lecture ; seule la table `jobs` est consultée.
- Recherche systématique d’un nombre, éventuellement une fourchette ou un signe `+`, suivi de `year(s) in` ou `year(s) track record`. Cette recherche est exhaustive pour ces formes, sans prétendre couvrir toutes les expressions d’expérience.
- Descriptions locales examinées avec leurs rubriques, ponctuation et phrases voisines ; aucune nouvelle consultation réseau. Les annonces n’ont pas été revérifiées sur les sites publics.
- Simulations sur copies profondes de `Job`, avec les règles actuelles et un minimum explicite fourni à la copie ; aucun recalcul enregistré, aucune modification du code, des candidatures ou de la base.

Le fichier local [experience-in-audit.json](../data/discovery/lot38/experience-in-audit.json) contient l’horodatage, le hash de la photographie des offres, les URLs, les hashes des descriptions, les extraits exacts et offsets, les minima actuels et les simulations. Le script local `data/discovery/lot38/audit_experience_in.py` permet de reproduire cette photographie.

## Huit formulations claires

| Société / offre | ID local | Preuve | Minimum / effet simulé |
| --- | --- | --- | --- |
| Jump — Quantamental Research Analyst, Singapore | `26e2a615-1c4c-4dfd-92cd-91bb072063b6` | Rubrique `Skills You’ll Need` : `3–6 years in buy/sell-side research, prop trading, ETF/index research, or corporate actions analysis` | 3 ; junior 20→0 ; score 0 conservé, exclusion `research analyst` conservée. |
| IMC — Trading Engineer - Strategy | `602f0bbe-c4e4-47ff-b17e-fd18d23ae096` | Rubrique `What You Bring` : `3+ years in site reliability, systems engineering, or technical operations, ideally supporting high-performance or real-time systems` | 3 ; junior 5→0 ; score 0 conservé. `Ideally` qualifie ici le contexte des systèmes, pas les trois ans. |
| Jump — Quantitative Developer, Trading Team | `278a2e7a-9b67-4321-8912-8431127e0183` | Rubrique `Skills You’ll Need` : `2+ year track record of solving challenging problems through coding with real metrics & impact in industry` | 2 ; déjà fourni par la donnée structurée ; score 0 conservé. Le texte n’est pas encore reconnu. |
| UBS — APAC Algo Trading Low Latency C++ Developer | `54c636ec-c11e-42b0-9f3d-a4a8a9a6c28d` | Rubrique `Your skills and experience` : `7+ years in FPGA (Verilog/VHDL) or low-latency C++ development` | 7 ; junior 5→0 et exclusion ≥5 ans ajoutée ; score 0 conservé. |
| Optiver — SSO Floor Trader | `1479311f-fd15-49e1-a415-700dcd583854` | Rubrique `Who you are` : `3+ years in options trading, market making, floor brokerage, or exchange operations.` | 3 ; score 66 conservé, junior déjà 0. |
| Optiver — SSO Floor Trader | `1652c8c1-67a6-4f21-b78e-452f6b069f76` | Même qualification. | 3 ; score 66 conservé, junior déjà 0. |
| Optiver — SSO Floor Trader | `6c56efe2-73cb-49c1-b39c-626f4f02f627` | Même qualification. | 3 ; score 66 conservé, junior déjà 0. |
| Optiver — SSO Floor Trader | `f645eafc-4598-48ff-8480-e55bf6ea0f45` | Même qualification. | 3 ; score 66 conservé, junior déjà 0. |

Chez Optiver, la phrase suivante commence par `Preferred: Prior listed options market-making experience.` Elle ne rend pas facultatif le minimum de trois ans de la phrase précédente. Les quatre annonces ne doivent pas être confondues avec DRW Floor Trader.

## Deux formulations à isoler

### Jump — Quantitative Developer, Hong Kong

ID `b8409c7c-9e90-4117-9844-984037cf05dc` : `5+ year track record ... in industry and/or academia`. La suite comporte également `Experience is a plus, but a strong desire to learn and grow is essential.`

Le texte demande une réalisation sur cinq ans pouvant inclure le monde académique ; cela ne démontre pas cinq années d’emploi professionnel. Le minimum structuré actuel vaut déjà **5**. Cet audit ne valide ni ne corrige cette métadonnée. Une extension du parseur ne doit pas utiliser cet exemple comme preuve générale que tout `track record` équivaut à de l’expérience professionnelle obligatoire. Définir et tester séparément le traitement des parcours académiques.

### Jane Street — HR Partner

ID `91c0b05c-5f62-4798-bf3a-340dfed127a0` : `around 10 years of experience in HR, including 5+ years in an HR Business Partner role`.

L’approximation de la durée totale et la sous-exigence de cinq ans sont imbriquées. Une règle qui étend `around` à toute la proposition peut manquer le sous-minimum ; une règle qui l’ignore peut transformer une attente indicative en exigence stricte. Ce rôle RH exclu ne justifie pas d’élargir la première correction sans tests consacrés à cette portée.

## Contrôles réels du corpus

| Cas | IDs | Résultat attendu |
| --- | --- | --- |
| Crédit Agricole CIB — deux Global Markets Trainee, contrats d’un an | `7172d606-821e-405f-9ef5-b23c4b0cd185`, `bc0ee704-794f-4f1b-8319-3709a2f1cd90` | `possible for extension up to 2 years in total` décrit la durée du programme. Ne pas en faire un minimum d’expérience. Les minima structurés zéro restent distincts. |
| Citi — Markets Control Assessment Lead | `05087323-bc21-4236-8bb8-36a3cf1dfd1d` | `5+ years in Risk & Controls roles` accompagne déjà un minimum textuel de 10 ans. Une extension ne doit jamais abaisser ce minimum. |
| Goldman Sachs — Issue, Events & Risk and Control Self-Assessment Management | `5f1fe210-182f-47fa-bb58-ed3e464e8f3b` | `3+ years in the Financial Services / Banking industry` ; minimum textuel de 3 déjà reconnu ailleurs. |
| Nomura — AI & Innovation Program Manager | `b001b737-9ca4-446b-bd41-61eb66b0b650` | `at least 2 years in AI/GenAI or digital transformation` ; minima textuels 2 et 8 déjà reconnus. Conserver le maximum 8. |

## Correction future bornée proposée

1. **Commencer par `N–M years in …` et `N+ years in …`**, avec bornes entières valides, borne basse conservée, et rubrique candidate reconnue. Ajouter explicitement les rubriques réelles `Skills You’ll Need` et `What You Bring` ; conserver le suivi des rubriques facultatives et institutionnelles. Refuser les fourchettes inversées, les durées contractuelles, les maxima et les phrases négatives.
2. Ne pas exiger littéralement le mot `experience` après `in` : c’est précisément le manque observé. Exiger en revanche une activité professionnelle et un contexte de qualification, avec un périmètre initial justifié par les exemples recensés.
3. Garder les alternatives de domaine (`research, trading, or analysis`) distinctes des alternatives qui dispensent de durée (`degree or 3 years`, `PhD instead`, `or no experience`). Détecter ces dernières avant de produire un minimum.
4. Préserver les préférences attachées au minimum (`3+ years in trading preferred`) ; ne pas propager la rubrique suivante `Preferred:` rétroactivement. Séparer aussi les préférences portant seulement sur le domaine, comme `ideally supporting high-performance systems`.
5. Traiter `track record` comme une extension séparée : le seul cas clair de deux ans est déjà couvert par la métadonnée structurée ; le cas de cinq ans autorise l’académie. Il n’est donc pas nécessaire d’élargir cette sémantique pour obtenir les sept nouvelles observations certaines de la première correction.
6. Vérifier sur les 814 offres, puis sauvegarder avant tout recalcul éventuel. Conserver les exclusions métiers étudiées au lot 37 ; reconnaître trois ans ne constitue pas une autorisation de promouvoir un Research Analyst ou un rôle SRE.

### Matrice de tests à ajouter lors de l’implémentation

- Positifs : les sept offres `years in` ci-dessus, fourchettes avec tirets Unicode, `0–2`, `2–5`, et préférence sur le seul domaine.
- Négatifs : deux durées Crédit Agricole, préférence de rubrique ou attachée à la durée, `not required`, `up to`, durée d’existence de société, borne inversée, alternatives académiques ou sans expérience.
- Portée : les deux phrases Optiver obligatoire puis Preferred, virgules dans les listes de métiers, descriptions ATS aplaties et retours à la ligne ; le titre junior ne doit pas effacer un minimum reconnu supérieur à deux ans.
- Non-régression : maxima Citi/Nomura préservés, données structurées conservées, scores exclus restant nuls, aucun effet sur les offres hors périmètre.

Ces tests sont proposés pour une future implémentation et ne sont pas présentés comme exécutés dans cet audit.
