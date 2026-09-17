# Provenance de l'expérience Jump — vérification indépendante du lot 40

## Résultat de la lecture des sources

Le rejeu des **deux annonces Jump auditées**, depuis leur capture Greenhouse locale, distingue désormais la durée de pratique attestée du minimum professionnel :

| Offre | Minimum numérique avant | Minimum professionnel extrait | Preuve conservée | Score simulé |
| --- | ---: | ---: | --- | ---: |
| Quantitative Developer, Hong Kong — `6172858`, ID `b8409c7c-9e90-4117-9844-984037cf05dc` | 5 | Non établi (`null`) | 5 ans ; `industry_or_academia` | 0 → 0 |
| Quantitative Developer, Trading Team — `7767735`, ID `278a2e7a-9b67-4321-8912-8431127e0183` | 2 | 2 | 2 ans ; `professional` | 0 → 0 |

Le premier texte exige un parcours de codage avec un impact `in industry and/or academia`. Le second précise `in industry`. **La durée cinq n'est pas supprimée de la preuve** ; elle cesse seulement d'être présentée comme un minimum professionnel certain. Dans les deux copies simulées, l'exclusion `software role without embedded trading evidence` demeure. Ce changement ne décide donc pas de l'adéquation métier de ces rôles hybrides.

## Origine vérifiée

La capture `data/discovery/lot32/capture-live/jump_trading.json`, SHA-256 `7ae8cfe810a1398e3289e800e55dc54b5209fd959d477a044ee2d64df515fb49`, est rejouée **ligne par ligne pour ces deux références uniquement**. Chaque HTML brut correspond exactement à la description stockée. Leurs métadonnées publiées portent le contrat, pas une durée numérique d'expérience : les nombres sont dérivés du texte par notre collecteur, comme établi dans l'[audit du lot 39](AMBIGUOUS-EXPERIENCE-LOT39.md).

Chaque objet `ExperienceEvidence` conserve le nombre, le domaine (`professional`, `industry_or_academia` ou `unspecified`), l'origine `description`, la méthode `jump_coding_track_record` et un extrait exact du texte aplati. Une phrase de codage sans domaine explicite conserve une preuve `unspecified`, sans devenir automatiquement une durée professionnelle.

La phrase ultérieure `Experience is a plus` ne suffit pas à annuler le parcours de codage obligatoire décrit dans la proposition précédente. Les préférences attachées directement à ce parcours sont, elles, écartées.

## Compatibilité et limites

- Les anciens payloads sans `experience_evidence` restent lisibles avec une liste vide. Charger ou recalculer une ancienne fiche **ne corrige pas silencieusement** son minimum historique : la réparation de la valeur dérivée demande une opération distincte, contrôlée et historisée.
- Les valeurs structurées d'autres collecteurs ne sont pas requalifiées par ce helper. L'absence de preuve typée n'affirme ni son origine, ni sa nature professionnelle ou académique.
- L'extraction reste limitée à la formulation de parcours de codage Jump et à la rubrique candidate auditée. Elle ne constitue pas une interprétation générale de toutes les qualifications académiques, alternatives ou durées professionnelles.
- L'expérience académique seule, les formulations inconnues et le cas Jane Street HR restent hors d'une nouvelle règle de classement. Aucune exclusion métier n'est levée.

## Validation indépendante réalisée

**22 tests autonomes** dans [test_experience_provenance_regressions_lot40.py](../tests/test_experience_provenance_regressions_lot40.py) ont réussi. Ruff et le contrôle de format sont conformes. Les tests couvrent les deux formulations réelles, la preuve exacte et son origine, le domaine inconnu, le zéro explicite, les préférences, les négations, l'histoire d'entreprise, les fourchettes et nombres invalides, la persistance des exclusions métier, la compatibilité des anciens payloads et les listes par défaut indépendantes.

Le rejeu utilise SQLite en `mode=ro`, `query_only=ON`, dans une transaction de lecture limitée aux deux offres ; aucun réseau, aucune lecture des candidatures et aucune écriture en base. Les scores sont calculés sur des copies.

L'artefact local [provenance-replay.json](../data/discovery/lot40/provenance-replay.json) contient les hashes des captures, descriptions, modèle et collecteur, les extraits avec offsets, les métadonnées employeur, les preuves extraites et les décompositions avant/après simulation.

## Revue de l'impact complet avant application

Le rejeu indépendant de **814 copies** valide l'impact final : deux fiches changent uniquement leurs champs dérivés d'expérience et, pour la fiche mixte, leur décomposition du score. **812 fiches restent strictement identiques et aucun total ne change.** La correction est idempotente sur tout le corpus. Les onze empreintes de tables SQLite correspondent encore exactement à la photographie `before.json`.

Les comptes simulés restent **812 actives, 161 prioritaires et 240 pertinentes**. Les catégories d'expérience deviennent 71 minima de 0–2 ans, 184 supérieurs à deux ans et 557 non reconnus. Les deux preuves ont été comparées aux lignes brutes archivées, jusqu'à l'extrait exact et à son origine ; les descriptions et l'exclusion métier sont préservées.

La revue du correctif et du stockage confirme la restriction aux trois champs autorisés, la validation avant écriture, les deux historiques associés et la transaction sous verrou prise par le workflow appelant. L'artefact [impact-review.json](../data/discovery/lot40/impact-review.json) accepte l'impact SHA-256 `eafade17d4816165a3c8731995989f6b9a9fa594141d52116aaefbaf75c8b287` et conserve les hashes des modules examinés.

**Cette acceptation porte sur la simulation avant application.** La sauvegarde, la répétition sur une restauration et la préservation des données après application doivent encore être attestées séparément dans la validation du lot.
