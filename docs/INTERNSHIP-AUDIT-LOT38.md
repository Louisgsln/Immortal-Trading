# Stages explicites sans marqueur dans le titre — audit du lot 38

## Conclusion

Le corpus contient **45 annonces Jane Street** dont le titre et le contrat ne signalent pas de stage, mais dont la description s'adresse directement au candidat comme stagiaire. **43 sont actives**, **20 n'ont aucune exclusion** et **six sont classées pertinentes** : trois Quantitative Trader à 65, trois Sales and Trading à 61, 57 et 57. Aucune n'atteint 70. Les autres valent déjà zéro, ce qui ne remplace pas une exclusion contractuelle indépendante.

Une correction limitée aux formulations explicites décrivant **le stage proposé au destinataire** est justifiée. Une recherche globale du mot `intern` ne l'est pas : elle exclurait notamment un Trader Crypto à 71 pour l'histoire de la société, et un Trader Deutsche Bank à 90 pour une expérience antérieure recevable.

## Méthode et portée

Audit indépendant en lecture seule de **814 offres**, dont 812 actives, 161 actives notées au moins 70 et 246 au moins 55, avant application du lot 38. Accès SQLite avec `mode=ro`, `query_only=ON` et transaction de lecture ; seule la table `jobs` est interrogée. Aucun réseau, aucune écriture en base et aucune lecture du suivi des candidatures.

Les candidats sont sélectionnés avec des formulations telles que `As an intern, you`, `As a … intern, you`, `During the internship, you/your`, `Over the course of your internship, you` et `You'll spend the bulk of your internship`. Le titre et le contrat sont contrôlés pour écarter les marqueurs déjà visibles de stage, Summer Analyst/Associate et Off-cycle. Cette sélection est un outil d'audit, pas une spécification complète du parseur de production.

L'artefact local [internship-audit.json](../data/discovery/lot38/internship-audit.json) contient les identifiants des 45 candidats, leurs six scores positifs, dix cas détaillés, l'URL de chaque cas, le hash SHA-256 des descriptions et celui de la photographie des offres. Les offsets sont des positions Unicode Python, base zéro, borne finale exclue, dans `description_text`. Les extraits et offsets ont été vérifiés sur cette photographie locale ; les pages publiques actuelles n'ont pas été consultées.

## Dix cas examinés

| Offre et ID local | Score initial | Preuve locale, offset `[début, fin)` | Décision |
| --- | ---: | --- | --- |
| Jane Street — Fundamental Research Analyst ; `146c550f-0d30-4fc1-a5f6-fe2d51305f3f` | 0 | `As an intern` [173,185) ; `As a Fundamental Analyst Intern` [318,349), suivis de `you'll` | Stage du destinataire. Ajouter l'exclusion stage indépendamment de `research analyst`, sans retirer cette dernière. |
| Jane Street — Quantitative Trader ; `0ac3bc87-3e91-41b8-addf-5cd1b57a67a2` | 65 | `During the internship` [1340,1361), suivi de `your work` ; `As a quantitative trading intern` [1681,1713), suivi de `you'll` | Stage explicite ; deux autres annonces équivalentes valent également 65. |
| Jane Street — Sales and Trading ; `0dc06d2e-1714-4ec9-9b19-d735bd647e86` | 61 | `As a Sales and Trading intern` [19,48), suivi de `you’ll work` | Stage explicite ; deux autres annonces valent 57. |
| Jane Street — Quantitative Researcher ; `52683156-71cf-4b7d-ba3a-1721ee73cbf7` | 0 | `spend the bulk of your internship` [902,935) | Le destinataire effectue le stage. Score déjà nul, mais aucune exclusion actuelle. |
| Jane Street — Tools & Compilers Research and Development ; `0a292fa8-a168-43e0-bf6d-aeb6a6df85ea` | 0 | `research internships` [46,66) et `During the internship` [1077,1098), suivi de `you will work` | L'offre décrit un stage de recherche ; ne pas se limiter à la formule `As an intern`. |
| Jump Trading — Trader \| Crypto ; `1a63f592-3e7b-4dd9-b287-493cc3c5c743` | 71 | `Since our inception as a skunkworks intern project` [295,345), puis `in late 2015` | Histoire de Jump Crypto ; préserver le rôle actuel `Full-time - Experienced`. |
| Citi — Markets, Quantitative Analysis, Full Time Associate, London, 2027 ; `0843609f-a940-4b1e-aa64-a674fa3c0757` | 0 | `Citi is looking for intern analysts` [487,522), mais `Quantitative Analysis associate program` [1272,1311) et `Time Type: Full time` [5285,5305) | Source contradictoire. Ne pas déduire un stage de `looking for intern` seul ; titre et développement du programme indiquent Associate. |
| Jane Street — Campus Recruiter ; `1d21c2bb-7941-4da2-adca-3eade46f4e03` | 0 | `find and hire outstanding interns` [81,114) ; `internship and in-house programme pipelines` [601,644) | Le candidat recrute les stagiaires. Ce n'est pas son contrat. |
| Deutsche Bank — IB - GEM Trader - Analyst ; `f3f5031e-0b59-4171-b21c-b9902de24986` | 90 | `gained through academic studies, internships` [1881,1925) | Expérience antérieure acceptée, contrat `Full time` : préserver le classement. |
| Susquehanna — Trading Systems Engineer Graduate: 2027 (Dublin) ; `130ff023-516f-40dc-b217-92f835ec0937` | 0 | `seeking talented graduates` [24,50), puis `interns enjoy weekly social events` [3334,3368) dans les avantages | Mention générique de stagiaires contradictoire avec le programme Graduate ; aucune exclusion stage automatique sur ce seul paragraphe. |

Les contrats des cinq cas positifs Jane Street sont absents (`null`). Le zéro des postes de recherche n'implique pas nécessairement une exclusion : la condition préalable de pertinence trading peut aussi donner zéro.

## Périmètre minimal proposé

1. Reconnaître les formulations qui lient explicitement le rôle actuel de stagiaire à `you`, `your work` ou au travail que le destinataire effectuera pendant **son** stage. Conserver la ponctuation et un contexte suffisant pour éviter les fragments historiques, les citations, les négations et les conditions.
2. Ajouter une exclusion contractuelle indépendante et explicable. Préserver les exclusions métier, la source, la description et le contrat source ; ne pas inventer `employment_type` à partir du parseur.
3. Tester les expériences passées, le recrutement/l'encadrement d'autres stagiaires, les anciens stagiaires, les liens vers un autre programme, les phrases citées ou niées et l'historique Jump. Un titre Graduate ne résout pas à lui seul une description contradictoire.
4. Mesurer le recalcul complet avant application. La sélection d'audit prévoit six pertes du seuil 55 et aucune du seuil 70 si ce sont les seuls scores modifiés : **246 → 240 offres actives pertinentes**, **161 prioritaires inchangées**. Ce chiffre est une projection de l'audit ; le rapport de validation doit publier l'impact réel du parseur retenu.

Les formulations moins directes, notamment certains Machine Learning Engineer ou Trading Desk Operations Engineer décrivant un programme sans l'une de ces phrases, restent hors de cette sélection minimale. Les titres comportant des homoglyphes ne sont pas corrigés par cet audit.
