# Deux exigences ambiguës — audit indépendant du lot 39

## Décision

**Conserver ces deux cas hors du correctif général `years in` du lot 39.** Le minimum Jump de cinq ans est structuré dans notre modèle, mais **inféré par notre collecteur depuis une phrase**, et non publié comme métadonnée numérique par l'employeur. Il couvre explicitement un parcours industriel **ou académique**. La phrase Jane Street imbrique une durée totale approximative et une sous-durée spécialisée.

Cet audit ne modifie ni les valeurs, ni les scores, ni le code. Le lot 39 conserve la valeur Jump existante ; cette conservation ne valide pas son interprétation comme cinq années d'emploi professionnel.

## Preuves et méthode

Lecture SQLite `mode=ro`, `query_only=ON`, transaction de lecture, limitée aux deux lignes `jobs` ci-dessous. Lecture des captures locales et du collecteur ; aucune requête réseau ni consultation des candidatures. Les simulations utilisent des copies en mémoire.

L'artefact local [ambiguous-audit.json](../data/discovery/lot39/ambiguous-audit.json) conserve les hashes des deux lignes, des descriptions et du collecteur, les extraits avec offsets Unicode base zéro, les métadonnées brutes et les résultats du rejeu. Les annonces publiques actuelles n'ont pas été revérifiées.

## Jump — Quantitative Developer, Hong Kong

ID local `b8409c7c-9e90-4117-9844-984037cf05dc`, référence employeur `6172858`, contrat `Full-time - Experienced`.

- Dans `Skills You’ll Need`, offsets **[2734,2857)** : `5+ year track record of solving challenging problems through coding with real metrics & impact in industry and/or academia.`
- Phrase distincte, **[2939,3012)** : `Experience is a plus, but a strong desire to learn and grow is essential.`
- Plus loin, **[3379,3501)** : plus de deux ans sur des bases de code industrielles est décrit comme `advantageous`, donc comme un avantage, pas un minimum professionnel établi.

### Origine exacte du cinq

Les captures `data/discovery/lot23/jump/catalogue.json` et `data/discovery/lot32/capture-live/jump_trading.json` ont le même SHA-256 : `7ae8cfe810a1398e3289e800e55dc54b5209fd959d477a044ee2d64df515fb49`. La ligne `6172858` contient une seule métadonnée : `Employment Type = Full-time - Experienced`. **Aucun champ numérique d'expérience n'y est publié.** Son HTML correspond exactement à celui stocké en base : SHA-256 `a8f72edb2c08d343de253e70a99a66a72e67153398e14de47cce2a4fa06dd26d`.

Le helper [jump_track_record_minimum](../src/trading_radar/greenhouse_filtered.py), documenté au [lot 23](EXPERIENCE-AUDIT-LOT23.md), repère le début de la phrase de codage dans la rubrique requise et renvoie `5`. `parse_board` affecte ce résultat à `minimum_experience_years`. Le rejeu local de la seule ligne brute reproduit cette valeur.

Le helper ne distingue pas `industry` et `academia`. Il écarte les préférences dans la même proposition, mais la phrase `Experience is a plus` est séparée par un point : elle n'annule pas ce cinq dans le code. Sémantiquement, cette préférence séparée **ne suffit pas non plus à prouver que le parcours de codage de cinq ans est facultatif**. Le problème certain est la confusion possible entre durée de pratique démontrée et durée d'emploi professionnel.

### Traitement futur recommandé

Conserver la preuve « cinq ans de pratique de codage, industrie ou académie », avec sa provenance et son domaine, tout en laissant **inconnu le minimum d'expérience professionnelle** lorsque l'annonce ne le précise pas. Cela demanderait de distinguer les types d'exigences dans le modèle et leur présentation avant de réviser la valeur historique ; simplement supprimer le cinq ferait perdre une exigence réelle de parcours.

Une alternative serait de définir explicitement le champ actuel comme toute expérience pertinente, professionnelle ou académique. Elle nécessiterait alors de revoir le libellé du dashboard et la règle d'exclusion automatique à cinq ans : cinq années académiques ne démontrent pas à elles seules une incompatibilité avec un recrutement junior professionnel. Ne pas généraliser l'actuel helper `track record` sans cette décision.

**Effet limité de la simulation :** retirer seulement le minimum de la copie fait passer junior de 0 à 5 et retire l'exclusion d'expérience ; le score reste **0**, grâce à `software role without embedded trading evidence`. Cette simulation ne recommande pas de lever cette exclusion métier.

## Jane Street — HR Partner, New York

ID local `91c0b05c-5f62-4798-bf3a-340dfed127a0`, référence employeur `8639148002`.

Dans `About You`, offsets **[1424,1539)** : `Have a bachelor's degree and around 10 years of experience in HR, including 5+ years in an HR Business Partner role`.

Le champ structuré vaut `null` et le parseur textuel ne fournit actuellement aucun minimum. Le score est **0 par classification NON_TRADING**, avec **aucune exclusion stockée** ; il serait inexact de parler d'une exclusion explicite RH existante.

`Around 10` décrit une durée totale approximative. `Including 5+` décrit une composante incluse, donc **ni quinze ans au total, ni dix ans comme minimum strict certain**. La lecture locale suggère cinq ans dans la spécialité, mais une règle générale doit décider si l'approximation du profil englobe cette sous-exigence ou seulement le total. Étendre automatiquement `around` à toute la proposition perdrait la distinction ; l'ignorer partout inventerait un minimum strict de dix ans.

**Traitement futur :** représenter séparément le total approximatif et la sous-exigence, puis tester les variantes avec sous-durée requise, indicative, préférée et alternative académique. La seule annonce non trading ne justifie pas d'élargir immédiatement la règle. Sur une copie dotée artificiellement du minimum cinq, une exclusion d'expérience apparaît mais le score reste **0** : cette absence de changement de total ne valide pas l'interprétation.

## Portée de la suite

Le prochain chantier de ces deux cas concerne la **provenance et la signification des durées**, avec correction contrôlée des valeurs dérivées éventuelles. Il est distinct de la reconnaissance des sept qualifications professionnelles certaines du lot 39. Aucune modification de collecteur, migration, correction de données ou extension à d'autres annonces n'est effectuée ici.
