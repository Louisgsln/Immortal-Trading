# Audit des qualifications et rubriques d’expérience — lot 28

## Conclusion

Le corpus justifie **une correction locale possible** : reconnaître le préfixe directement attaché `Experience Desirable:` comme une préférence. Une annonce Crédit Agricole CIB conserve actuellement `[1]` alors que son paragraphe HTML présente explicitement cette expérience comme souhaitée. Cette correction ne changerait pas son score de 82 : une année est déjà sous le seuil de pénalisation, et le minimum structuré de l’employeur est 0.

La revue n’a pas établi de minimum à retirer à cause d’une alternative diplôme/expérience. Plusieurs alternatives au diplôme coexistent avec une exigence d’expérience indépendante, qui doit être conservée. Un cas Susquehanna présente plutôt une expérience additionnelle non extraite ; il nécessite un périmètre distinct.

Cet audit ne modifie ni code, ni configuration, ni base. Il ne détermine pas l’éligibilité du candidat.

## Méthode et preuve

- Lecture de **813 offres**, dont **811 actives**, dans `data/jobs.db`, avec SQLite `mode=ro`, `PRAGMA query_only=ON`, transaction `BEGIN` puis `ROLLBACK`, sans `Repository`.
- Parseur actuel `required_experience_years` dans `src/trading_radar/scoring.py`, après les corrections du lot 26. **188 offres** produisent au moins un minimum.
- Aucun accès réseau : les textes correspondent aux annonces déjà conservées, sans confirmation de leur état public actuel.
- Preuve : [qualification-audit.json](../data/discovery/lot28/qualification-audit.json). Elle contient les motifs exacts, tous les IDs signalés, les 813 résultats du parseur, les neuf cas examinés avec URL et identifiant externe, les extraits exacts et leurs offsets `[start, end)` dans `description_text`, les SHA-256 des descriptions, ainsi que les empreintes des onze tables lues.
- SHA-256 du fichier de parseur utilisé : `4ff41de210061d8921f9b9ad261085cbfba5eba9acb000c284ed5e81a0efaf0c`.

### Signalement automatique, avant interprétation

| Recherche heuristique | Offres signalées | Interprétation permise |
| --- | ---: | --- |
| `Experience Desirable/Preferred`, `Preferred/Desirable Qualifications/Experience` | 46 | Présence d’un marqueur, parfois dans une phrase et non un titre |
| `Preferred Qualifications/Experience` ou `Experience Desirable`, puis nombre d’années dans les 900 caractères | 3 | Trois candidats à examiner ; aucune propagation automatique de rubrique |
| Diplôme, `or`, expérience dans des fenêtres de 80–100 caractères | 142 | Recherche large comprenant des faux positifs, notamment des choix de spécialité |
| Alternative explicite `or equivalent … experience`, substitution ou `in lieu` | 37 | Alternative possible à l’éducation, sans conclusion sur les autres exigences |
| Diplôme puis `or N years` dans les 150 caractères | 0 | Absence de ce motif seulement, pas absence exhaustive d’alternatives |

Les décomptes sont par offre, pas par occurrence. Neuf cas ont fait l’objet de la revue ciblée ci-dessous ; les 142 candidats larges n’ont pas tous reçu une revue sémantique exhaustive. Les recherches ne couvrent pas toutes les langues, toutes les formulations ou toutes les distances entre un titre et ses éléments.

## Neuf cas vérifiés

Les extraits complets avec positions, URL et empreintes sont dans la preuve JSON. Les attentes ci-dessous décrivent des critères pour une éventuelle correction, pas une modification déjà appliquée.

| Offre et ID local | Extrait déterminant | Extraction actuelle | Décision proposée |
| --- | --- | --- | --- |
| Crédit Agricole CIB — Analyst, Sales SLT & CRI Americas — `6b436a14-8f02-4846-b09d-c217a0422f1a` | `Experience Desirable: 1+ years of relevant experience in banking, preferably in Project Finance and Digital Infrastructure` | `[1]`, minimum structuré `0` | Préfixe de préférence direct : attendre `[]` pour le texte ; préserver le minimum structuré |
| Goldman Sachs — Quant Coverage Associate Hong Kong — `c40698a3-52eb-4156-9fe8-116cb6ce05a7` | `PREFERRED QUALIFICATIONS Minimum of 1 year work experience in Equities` | `[]` | Conserver le résultat du lot 26 |
| Goldman Sachs — Prime Margin Lending Analyst Hyderabad — `b6bc3c34-806d-4e6d-b01c-c608ed172a80` | `Preferred Qualifications • At least 2 years of experience in Operations or related field` | `[]` | Conserver le résultat du lot 26 |
| Goldman Sachs — Software Engineer, Front Office Technology — `d7733901-9db2-487f-9b66-2c38b7e93c1b` | `Advanced degree in Computer Science (or equivalent work experience). Minimum 2 years of relevant professional experience` | `[2]` | Conserver : le diplôme admet un équivalent, le minimum est indépendant |
| BNP Paribas — Assistant Manager, Java Full Stack — `983c987c-3823-4b13-b0ad-b63a045ece59` | `Minimum 8 years of experience along with bachelor’s degree in the related field or equivalent experience.` | `[8]` | Conserver : `along with` ajoute le diplôme ou son équivalent au minimum |
| Citi — US Agency Trader — `18aa57c3-77d5-4f8b-956f-b4f4eea90bb7` | `Qualifications: 10+ years of experience in a related role` puis `Education: Bachelor’s degree/University degree or equivalent experience` | `[10]` | Conserver : les rubriques distinguent les deux contraintes |
| Susquehanna — Quant Developer, Trading Strategies, Experienced Hire — `3f757767-f462-42b5-8a87-9571611cc84d` | `Bachelor's degree … or its foreign equivalent plus 7 years of progressive experience developing software applications. Relevant technical experience may substitute for education` | `[]` | Périmètre ultérieur : étudier l’extraction additive de `plus 7 years` avec attendu `[7]` ; la substitution porte sur l’éducation |
| Macquarie — Electronic Sales Trader — `adb32e56-b87c-4147-981d-ef468df63f69` | `Strong academic background, ideally in finance, economics or a quantitative discipline 5+ years of relevant experience` | `[5]` | Conserver : `ideally` qualifie la discipline du diplôme |
| Société Générale — FIC Derivatives Structurer — `476a02fc-6c30-402a-a06f-62790d1018c7` | `You have at least 3 years of experience in financial markets, ideally gained within a structuring, pricing, trading or derivatives sales team.` | `[3]` | Conserver : `ideally` qualifie le domaine des trois années |

### Structure conservée du cas Crédit Agricole CIB

Le champ HTML `description` contient successivement :

```html
<p>0-2 years</p>
<p>Experience Desirable: 1+ years of relevant experience in banking, preferably in Project Finance and Digital Infrastructure</p>
<p>Competencies Essential: ...</p>
```

La dernière ligne est abrégée ici ; la preuve JSON conserve le paragraphe d’expérience exact, ses offsets dans le HTML et l’empreinte du HTML complet. Le texte d’expérience commence à l’offset **4038** de `description_text`. Le mot `Desirable` qualifie directement l’expérience, et non un diplôme ou un domaine éloigné.

## Prochain périmètre falsifiable

1. Reconnaître **uniquement** `Experience Desirable:` directement avant une expression d’expérience déjà reconnue. Ne pas étendre automatiquement la préférence jusqu’au prochain titre dans le texte aplati.
2. Ajouter le cas réel CA avec attendu `[]`, puis les contre-exemples : `Education Desirable: … 5+ years of experience` conserve `[5]`, et `Experience Desirable: Python. Requires 3 years experience.` conserve `[3]`.
3. Conserver les deux exemples Goldman déjà corrigés et les cinq minima indépendants du tableau. Un minimum structuré fourni par l’employeur reste applicable indépendamment de la préférence textuelle.
4. Comparer les **813 listes**, scores, exclusions et raisons avant/après. Pour ce micro-périmètre, attendre **une seule liste modifiée**, CA `[1] → []`, et aucun score modifié. Tout écart supplémentaire doit être examiné et expliqué avant livraison.
5. Traiter `degree … plus 7 years` dans un lot séparé, avec analyse de la portée de `or` et `substitute for education`. Mesurer le résultat sur le corpus avant de généraliser ; ne pas annuler toutes les exigences d’une annonce au seul motif qu’elle contient `or equivalent experience`.

Le corpus signalé ne justifie pas actuellement une propagation générale des rubriques préférées. L’absence d’un cas observé à distance supérieure à cette fenêtre n’est pas une preuve d’absence : la structure HTML et les limites de listes devront être conservées ou reconstruites pour élargir ce périmètre de façon contrôlable.
