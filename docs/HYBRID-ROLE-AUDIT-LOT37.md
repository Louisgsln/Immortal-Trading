# Rôles hybrides — audit indépendant du lot 37

## Conclusion

**Aucune correction isolée de classification n’est suffisamment justifiée pour être appliquée dans ce lot.** Les deux rôles hybrides signalés au lot 32 mêlent trading et exploitation technique, avec des responsabilités explicites de support de production. Le poste Jump Research Analyst possède des missions de trading établies, mais son minimum de trois ans n’est toujours pas reconnu : supprimer son exclusion seule ferait passer son score de **0 à 88**, avec une compatibilité junior erronément maintenue à 20/20.

Les exclusions, les scores, les données et le code de production restent inchangés. Cette conclusion concerne sept cas étudiés, sans prétendre qualifier tous les postes techniques du corpus.

## Méthode et preuves

Lecture du corpus local de **814 offres**, puis examen de sept descriptions : SQLite `mode=ro`, `query_only=ON`, transaction de lecture et seule table `jobs` interrogée. Aucun réseau, aucune lecture du suivi des candidatures, aucune écriture dans la base. Les simulations utilisent des copies profondes de `Job` et une copie des mots-clés ; elles ne constituent pas un recalcul appliqué.

Le fichier local [hybrid-role-audit.json](../data/discovery/lot37/hybrid-role-audit.json) conserve l’horodatage, le hash de la photographie des offres, les URLs, les scores, les exclusions, les minima reconnus, les hashes des descriptions et les extraits avec offsets exacts. Les sept scores et exclusions rejoués correspondent aux valeurs stockées. Les descriptions sont celles déjà conservées ; leur disponibilité publique actuelle n’a pas été revérifiée.

## Trois cas prioritaires

| Offre | ID local | Score / exclusion | Preuve et décision |
| --- | --- | --- | --- |
| IMC — Trading Engineer - Execution | `f04aa0df-f736-4e73-8359-fb703e06e810` | 0 ; `software role without embedded trading evidence` | Support opérationnel des systèmes en direct, rotations de support, réseau et disponibilité. Minimum reconnu : 2 ans, issu de `2-5+ years`. Rattachement au trading établi, mais dominante SRE/production : conserver l’exclusion en attendant une définition explicite de l’adéquation de ces fonctions au périmètre recherché. |
| Jump — Quantitative Developer \| Trading Team | `1c24a2a1-a702-4131-a63c-d75f1aed9c8c` | 0 ; même exclusion | L’employeur décrit une « hybrid development and research and trading operations position ». Escalade, surveillance, fiabilisation du pipeline et support utilisateurs. Minimum reconnu : 2 ans. Une mention de trading en direct ne démontre pas, seule, une mission de décision de marché ou de développement des stratégies. |
| Jump — Quantamental Research Analyst \| Trading Team | `26e2a615-1c4c-4dfd-92cd-91bb072063b6` | 0 ; `research analyst` | Recherche sur les prix ETF et stratégies avec les traders ; détermination de juste valeur et génération d’idées de trades. Ce n’est pas uniquement de la recherche éloignée du trading. Cependant la rubrique de qualifications exige `3–6 years in buy/sell-side research, prop trading, ETF/index research, or corporate actions analysis`, actuellement non reconnue. |

### Conséquence d’une levée prématurée de Research Analyst

Sur la seule copie en mémoire de l’offre Jump :

| Simulation | Score | Composante junior |
| --- | ---: | ---: |
| Règles actuelles | 0 | 20 |
| Retrait du seul terme d’exclusion `research analyst` | 88 | 20 |
| Même retrait et minimum explicite de 3 ans fourni à la copie | 68 | 0 |

Le dernier scénario illustre la nécessité de traiter ensemble métier et expérience. Il ne recommande ni d’injecter cette valeur manuellement en production, ni d’admettre tous les Research Analyst.

## Contrôles et cas voisins

- **IMC Trading Engineer - Strategy**, `602f0bbe-c4e4-47ff-b17e-fd18d23ae096` : score 0, même exclusion logicielle. Missions de surveillance et de fiabilité en temps réel. La qualification `3+ years in site reliability, systems engineering, or technical operations` n’est pas reconnue. Le mot Strategy du titre ne suffit donc pas à justifier une promotion dans le classement.
- **Jump Quantitative Developer | Trading Team**, `278a2e7a-9b67-4321-8912-8431127e0183` : score 0, même exclusion. Un projet possible concerne la microstructure, tandis que les autres concernent production, déploiement et pipelines. `2+ year track record of solving challenging problems through coding with real metrics & impact in industry` n’est pas reconnu. L’annonce ne permet pas de garantir la répartition réelle des missions ; conserver cette incertitude.
- **Jane Street Fundamental Research Analyst**, `146c550f-0d30-4fc1-a5f6-fe2d51305f3f` : score 0 pour `research analyst`. La description contient explicitement `As an intern` et `As a Fundamental Analyst Intern`, malgré un titre sans Intern. Toute future exception Research Analyst doit conserver une protection contre ce stage. Supprimer le terme globalement ferait disparaître son unique exclusion actuelle.
- **XTX C++ Software Engineer**, `34f9ad24-1ae7-4463-8b71-a2175dadd5d8` : contrôle positif, score 65, aucune exclusion, indice vérifié `trading_technology`. Le rôle réalise les idées de trading et intervient de la réception des données de marché à l’envoi des ordres. Ce signal validé ne peut pas être transféré aux postes SRE uniquement parce qu’ils citent le trading.

## Suite précise proposée

1. Conserver les exclusions actuelles pour les rôles hybrides opérationnels examinés. Ne pas ajouter globalement `live trading` ou `trading team` aux expressions qui permettent d’éviter l’exclusion.
2. Pour une future exception Research Analyst, exiger des preuves de missions dans le corps du rôle : conception d’idées de trades, valorisation/pricing lié aux décisions et collaboration directe avec les traders. Les paragraphes institutionnels ou le seul titre ne suffisent pas.
3. Avant cette exception, corriger et tester la reconnaissance contextualisée des qualifications `N–M years in …`, `N+ years in …` et éventuellement `N+ year track record …`. Préserver les préférences, les alternatives académiques, les durées d’existence des sociétés et la borne basse des fourchettes. Mesurer l’impact sur tout le corpus avant application.
4. Ajouter des contre-exemples de stages explicites sans Intern dans le titre, ainsi que les deux rôles de support et le contrôle positif XTX. La levée d’une exclusion métier ne doit jamais effacer une exclusion contractuelle ou d’expérience indépendante.

Cet audit fournit des preuves pour cette suite ; il n’implémente aucun de ces changements.
