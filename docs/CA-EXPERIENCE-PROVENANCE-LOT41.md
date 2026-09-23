# Provenance de l’expérience CA CIB — audit préalable du lot 41

Cet audit décrit l’état antérieur au correctif. L’extension du modèle, les
contrôles de bornes et la validation finale sont suivis dans le
[bilan du lot 41](VALIDATION-LOT41.md).

## Résultat

Les **24 annonces Crédit Agricole CIB** de la base sont présentes dans la collection archivée du lot 7. **21 disposent d’un minimum structuré**, concordant avec le champ employeur exact `fldapplicantcriteria_experiencelevel` ; trois n’ont pas ce champ. Les 24 identités, descriptions et minima sont concordants après relecture des champs archivés.

| Minimum enregistré | Annonces | Valeurs originales du champ |
| --- | ---: | --- |
| 0 | 9 | `0 - 2 ans` (1), `0-2 years` (8) |
| 3 | 2 | `3-5 years` (2) |
| 6 | 8 | `6 - 10 ans` (7), `6-10 years` (1) |
| 11 | 2 | `11 ans et plus` (2) |
| Absent | 3 | Champ absent |

Les trois références sans champ sont `2026-114600`, `2026-108239` et `2026-112620`. Aucun minimum ne doit leur être attribué par cette extension de provenance.

## Origine vérifiable

La base ne conserve plus `raw_payload` pour ces 24 annonces. En revanche, `data/discovery/lot7/credit_agricole_cib_collection.json` conserve leurs `raw_payload.fields`, dont les valeurs précises du champ d’expérience et les champs ayant construit la description.

L’audit reconstruit des conteneurs HTML à partir de ces champs archivés, puis appelle `parse_detail`. Il vérifie l’identité normalisée, l’intégralité de la description source et du texte normalisé, ainsi que le minimum enregistré. **Il s’agit d’un rejeu des champs archivés, pas d’un rejeu de 24 captures HTML originales.**

Une capture HTML originale est disponible dans le lot 7 : `8a62882a611a.html`, référence `2026-115317`. Ses champs sont exactement égaux à ceux de la collection archivée ; son parsing produit le même résultat que le rejeu des champs. Les 23 autres annonces reposent sur la collection archivée et les contrôles de concordance, sans prétendre disposer de leur HTML original.

La valeur `0-2 years` apparaît aussi dans les descriptions aplaties. Cette occurrence n’est pas utilisée pour reconstruire sa provenance : **le champ employeur identifié fournit la preuve**. Les minima zéro restent des minima publiés, sans garantie d’éligibilité ni suppression d’autres exclusions.

## Limites du parseur actuel

Aucune fourchette inversée ni préférence n’apparaît dans les valeurs archivées. Des sondes synthétiques, séparées du corpus, montrent toutefois que le parseur actuel :

- accepte à tort `6 - 3 ans` et `3-2 years` en conservant la borne de gauche ;
- refuse les préférences ajoutées (`0-2 years preferred`, `Preferred 0-2 years`) ;
- ne reconnaît pas `0–2 years` avec un tiret Unicode ;
- refuse les nombres négatifs ou décimaux ; une valeur `100-101 years` provoque une erreur de validation du modèle.

Une extension sûre devrait valider les deux bornes, leur ordre et la plage 0–99. Ces contrôles ne changeraient aucun minimum des 24 annonces observées. L’élargissement aux tirets Unicode peut être testé séparément sans être nécessaire pour enrichir les 21 preuves présentes.

## Proposition de périmètre

Ajouter une preuve d’origine **champ employeur**, avec l’identifiant `fldapplicantcriteria_experiencelevel`, la valeur originale exacte et la méthode CA CIB. Conserver le minimum numérique actuel pour les 21 valeurs concordantes, sans transformer la description aplatie en preuve de champ et sans rétablir arbitrairement tout `raw_payload`.

Le modèle du lot 40 ne permet pour l’instant que l’origine `description` et la méthode `jump_coding_track_record` : il devra être étendu explicitement. Le recalcul, la persistance et l’interface ne sont pas modifiés par cet audit.

## Preuve et méthode

[ca-provenance-audit.json](../data/discovery/lot41/ca-provenance-audit.json) contient les 24 identités locales, les valeurs de champ, les minima, les contrôles de concordance et les hashes de la collection, des champs, des descriptions, de l’unique capture HTML et de la photographie des 814 offres.

SQLite a été ouverte avec `mode=ro`, `PRAGMA query_only=ON` et une transaction de lecture. Seule la table `jobs` a été consultée. Aucun réseau, aucune écriture en base, aucun changement de code ni opération Git.
