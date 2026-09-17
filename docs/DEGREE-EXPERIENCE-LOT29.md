# Expérience explicitement ajoutée au diplôme — lot 29

## Résultat

Le helper `degree_experience_years` reconnaît le minimum de **7 années** d'une annonce Susquehanna que les expressions précédentes ne reconnaissaient pas. Il ne modifie pas la base et ne généralise pas le libellé « Experienced Hire » en exigence numérique.

Le rejeu du helper sur les **813 descriptions** conservées retourne une liste non vide pour **une seule offre** :

| Champ | Valeur |
| --- | --- |
| ID local | `3f757767-f462-42b5-8a87-9571611cc84d` |
| Employeur / titre | Susquehanna — Quant Developer, Trading Strategies, Experienced Hire |
| Ancienne extraction | `[]` |
| Extraction additionnelle | `[7]` |
| SHA-256 de `description_text` UTF-8 | `738e64d8ac34ddaceaea72dcdb270cada82557a8674513afa0383f2f9c881454` |

Extrait conservé :

> What we're looking for Bachelor's degree in Computer Science, Engineering, Mathematics or related discipline or its foreign equivalent plus 7 years of progressive experience developing software applications. Relevant technical experience may substitute for education

`plus` ajoute l'expérience au diplôme ou à son équivalent étranger. La phrase suivante permet de remplacer **l'éducation** par de l'expérience ; elle n'annule pas les sept années de la première phrase.

## Audit du corpus

Lecture SQLite avec `mode=ro`, `PRAGMA query_only=ON`, transaction `BEGIN`, puis `ROLLBACK`, sans `Repository`, sans réseau et sans écriture des annonces.

La recherche préalable a sélectionné les mots `degree`, `bachelor`, `master`, `doctorate` ou `phd`, puis `plus` dans les 350 caractères de la même phrase, avec arrêt sur `. ; ! ?` et retour à la ligne. Elle a signalé **27 offres**. Une seule contient `plus` suivi immédiatement d'un nombre : le cas Susquehanna ci-dessus. Les autres occurrences qualifient des atouts (« a plus ») ou ne lient pas ce mot à un minimum numérique.

Exemples de faux positifs de cette recherche large, ignorés par le helper :

| ID | Formulation observée | Lecture |
| --- | --- | --- |
| `81bed804-550d-426f-b40a-5ea027cd2d79` | `Having a project management or engineering degree is a plus` | Diplôme souhaité, pas expérience additive |
| `ec8421a9-760f-4bc4-80db-77b6eed7e055` | `bachelor’s degree and 5+ years of experience ... Having experience ... is a plus` | Les cinq années sont déjà reconnues ; le `plus` éloigné est une préférence |
| `549bfc95-f61d-4cc6-b31f-082f8e02b2dc` | `degree ... is a plus. At least 4 years of professional experience` | Deux phrases distinctes ; le minimum indépendant reste au parseur existant |
| `ec012579-f711-4080-a090-e4ae979bf2db` | `degree or equivalent experience, Master degree a plus` | Alternative au diplôme, sans minimum numérique ajouté |
| `f8d77a74-bdcf-4db2-ad78-cd7f956bd57c` | `foreign equivalent 5+ years ... prediction markets is a plus` | Les cinq années sont déjà reconnues ; aucun connecteur `plus N years` |

Cette recherche et ce helper ne constituent pas un parseur exhaustif de l'éligibilité ou de toutes les langues.

## Grammaire volontairement bornée

- Un diplôme explicitement nommé `degree`, éventuellement précédé de bachelor/master/university/college/advanced.
- Au plus **180 caractères** entre le diplôme et `plus`, sans franchir de phrase, point-virgule ou ligne.
- `plus N years ... experience`, avec un entier de 0 à 99, `N+` ou plage numérique croissante. Les plages apportent leur borne basse.
- Au plus trois qualificatifs parmi relevant/progressive/professional/related/technical/work/working avant `experience`.
- Une seule formulation additive et un seul diplôme dans la proposition. Les alternatives de parcours, substitutions, dispenses et préférences explicites rendent la proposition ambiguë et l'écartent.
- Tout `or` précédant le diplôme ou suivant l'expression d'expérience écarte la proposition. Cette règle ne dépend pas d'une liste d'abréviations de diplômes et couvre notamment `or MSc`, `or an MBA` et `or M.Sc.`.
- Une proposition suivante commençant par `or`, `alternatively` ou `instead` écarte aussi la première branche, même après un point, point-virgule ou retour à la ligne.
- `or related discipline` et `or its foreign equivalent` peuvent appartenir au diplôme sans supprimer l'expérience additionnelle.
- Les indices d'histoire d'entreprise, de salaire ou de biographie sont écartés. Les années d'âge et les nombres sans le mot `experience` ne correspondent pas à la grammaire.

La préférence est volontairement traitée de façon prudente sur toute la proposition. Ainsi, un `preferably` qui qualifie seulement un domaine peut empêcher cette **nouvelle** extraction ; cela n'efface aucun minimum trouvé par les expressions antérieures. Les listes HTML aplaties, les abréviations séparées par des points et les alternatives implicites peuvent aussi rester non reconnues. Leur extension demanderait un traitement structurel distinct.

## Vérification et intégration

**72 tests ciblés** couvrent l'extrait réel, les plages et bornes inversées, la déduplication, les frontières, les diplômes alternatifs, les préférences et les formulations sans exigence d'expérience. Les 29 tests de régression indépendante passent également après intégration. Ruff et mypy sont également exécutés sur le nouveau module.

L'intégration doit appeler ce helper sur le texte brut **avant** la normalisation historique des plages et de la ponctuation, puis fusionner ses minima avec ceux du parseur existant. Le rejeu global des scores et l'éventuelle application en base sont suivis dans le bilan du lot 29 ; ils ne sont pas exécutés par ce sous-agent.
