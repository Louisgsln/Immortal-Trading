# Provenance des minima Nomura professionnels — audit du lot 41

## Conclusion

Sur **16 offres actives** de la source `nomura_professionals`, **sept possèdent un minimum structuré** : zéro une fois, un une fois, deux trois fois et trois deux fois. Les sept valeurs sont reproduites exactement depuis le libellé **Experience** des descriptions. **Corporate Title ne fournit aucun nombre** : il produit seulement un indice de séniorité indépendant.

Aucune erreur de minimum n'est démontrée sur ces sept annonces. Deux préférences portent sur le domaine de travail, pas sur la durée. Le helper actuel présente toutefois des limites reproductibles sur des exemples synthétiques : il parcourt toute la description sans contrôle de rubrique et accepte une préférence, une fourchette inversée ou une alternative au diplôme. Une future preuve typée ne devrait donc pas déclarer indistinctement toute extraction `Experience` comme minimum professionnel obligatoire.

## Sept valeurs et leur origine

| Référence employeur | Offre | Libellé publié dans Position Specifications | Minimum / score actuel |
| --- | --- | --- | --- |
| `1373072800` | Trading Support | `Experience 1-3 years` | 1 / 92 |
| `1405548900` | GM-Global Markets | `Experience 0-2 years of experience preferably in Securitisation Market covering ABS/RMBS/CMBS` | 0 / 74 |
| `1397978500` | GM-Global Markets | `Experience 2+ years of experience in Securitisation Market covering ABS/RMBS/CMBS in European or US markets` | 2 / 53 |
| `1283059800` | GM-Global Markets | `Experience 2 - 4 years` | 2 / 74 |
| `1424280700` | Trading Support | `Experience 2 - 10 years` | 2 / 90 |
| `1339221200` | GM-Global Markets | `Experience 3 -5 years` | 3 / 54 |
| `1372610900` | GM-Global Markets | `Experience 3-5 years of experience preferably in Securitisation Market covering ABS/RMBS/CMBS in European or US markets` | 3 / 54 |

Quatre de ces sept fiches atteignent 70. Les bornes basses des fourchettes sont conservées ; `2 - 10` ne signifie ni dix ans minimum ni un poste garanti junior. Les champs Qualification qui suivent décrivent des diplômes distincts ; aucune alternative académique à la durée n'a été trouvée dans ces sept passages.

Les deux occurrences `preferably in Securitisation Market` qualifient le **domaine**, sans rendre facultatives les durées précédentes. Aucun de ces minima ne provient d'une durée de contrat. Contrôle réel distinct : Temp Analyst (Structuring), référence `1391694200`, décrit un contrat de douze mois ; `role_metadata` ne lui attribue aucun minimum d'expérience.

## Chaîne de provenance

Dans [nomura_professionals.py](../src/trading_radar/nomura_professionals.py), `parse_detail` extrait le texte de `jobdescription`, appelle `role_metadata`, puis stocke son résultat dans `minimum_experience_years`. Le motif numérique commence par `Experience`, retient la borne basse éventuelle et prend le maximum s'il trouve plusieurs occurrences. Il est actuellement appliqué au texte complet, **pas à une section bornée par le code**.

Le motif `Corporate Title` est distinct : Analyst peut produire `junior`, VP/Director et leurs variantes produisent `senior`. Le champ numérique n'est pas déduit du grade. De même, la liste `raw_payload.experience_minima` présente dans l'aperçu local est créée par notre parseur ; elle n'est pas une métadonnée numérique ATS indépendante.

## Rejeu local et niveau de preuve

- SQLite ouverte en `mode=ro`, `query_only=ON`, transaction de lecture ; seules les 16 offres de cette source sont examinées. Aucun réseau, aucune candidature consultée, aucune modification de code ou de base.
- `role_metadata` reproduit **16/16 minima et indices de séniorité stockés**, y compris les neuf minima absents.
- Les **16 descriptions** du fichier `data/discovery/lot14/nomura_professionals-preview.json` correspondent exactement à celles en base.
- Six fiches HTML complètes sont présentes dans la capture inspectée du lot 14 et rejouées avec `parse_detail`. Descriptions, minima et indices concordent. **Deux seulement portent un minimum** : `1373072800` et `1283059800`. Les cinq autres minima disposent de l'aperçu normalisé concordant ; cet audit ne prétend pas avoir rejoué leurs pages HTML complètes.

L'artefact local [nomura-audit.json](../data/discovery/lot41/nomura-audit.json) conserve les identifiants, URLs, empreintes des descriptions, offsets exacts des sept libellés, hashes des captures, paramètres du rejeu et photographie des 16 lignes. Il sépare les observations du corpus des contre-exemples synthétiques.

## Limites reproduites, sans erreur réelle attribuée au corpus

| Entrée synthétique du helper | Résultat actuel | Risque |
| --- | ---: | --- |
| `Preferred Experience: 5+ years in trading.` | 5 | Une préférence devient un minimum. |
| `Experience: 5-2 years.` | 5 | La borne inversée n'est pas rejetée. |
| `Qualification: a degree or Experience: 5 years.` | 5 | Une alternative au diplôme devient un minimum universel. |
| `Contract duration: 2 years.` | Aucun | Cette durée seule ne correspond pas au motif. |
| `Corporate Title: Analyst. Experience: 3-5 years.` | 3, indice junior | Grade et durée restent deux informations distinctes. |

## Suite bornée proposée

Une extension de provenance peut commencer par les libellés réels `Position Specifications → Experience`, avec extrait exact et origine **description**, en distinguant le grade, la durée et la qualification académique. Avant d'élargir ce helper, ajouter les protections de préférences, négations, alternatives et bornes inversées, puis mesurer les effets sur les 16 offres. L'audit ne recommande **aucun recalcul correctif immédiat** sur ces sept valeurs et ne constitue pas une validation des autres formulations d'expérience Nomura.
