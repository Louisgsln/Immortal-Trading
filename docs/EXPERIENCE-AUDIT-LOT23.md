# Audit des exigences d'expérience — lot 23

17 septembre 2026. Analyse locale des descriptions et calculs de score en mémoire. Les opérations de cet audit n'importent aucune offre, ne modifient pas SQLite et n'envoient aucune notification. La collecte et l'import Jump éventuels du lot sont validés séparément.

## Corrections bornées

Le score normalisait les tirets avant d'interpréter les durées. `2-5+ years` devenait `2 5+ years`, ce qui transformait à tort la borne supérieure en minimum de cinq ans. Les intervalles numériques suivis de `year` ou `years` sont désormais réduits à leur borne inférieure **avant** la normalisation. Les tirets courts, demi-cadratins et cadratins sont reconnus. Un intervalle inversé n'est pas utilisé comme preuve.

Les trois motifs antérieurs d'exigence sont conservés : minimum explicite, expérience suivie de `required`, et expérience numérique avec `+`. Les formulations `minimum 5 years working...` et `8+ years hands-on experience` restent reconnues. Un qualificatif directement associé, comme `Preferably 7+ years experience` ou `5+ years experience is a plus`, n'est pas un minimum obligatoire. En revanche, `7+ years experience, preferably in futures` conserve son minimum : la préférence concerne le domaine. Un historique explicitement attribué à l'entreprise n'est pas une exigence du candidat.

Cette correction ne constitue pas une compréhension générale des annonces. Les préférences éloignées du nombre, les alternatives entre diplômes et expérience et les formulations non couvertes restent à examiner. Une borne de trois ou quatre ans retire toujours les points de compatibilité junior. Une borne de deux ans ne prouve pas à elle seule qu'un poste est junior ; les autres exclusions et la classification technique s'appliquent toujours.

### Preuve spécifique Jump

La phrase vérifiée `5+ year track record of solving challenging problems through coding` est reconnue uniquement au début d'une proposition de la rubrique `Skills You'll Need` de Jump. Le nombre devient `minimum_experience_years`. Les rubriques `Nice to Have`, `Preferred Qualifications`, `Benefits` et `About Us` terminent la zone analysée. Une préférence dans la même proposition, une introduction d'entreprise, un autre type d'historique ou une rubrique ambiguë ne produit pas ce minimum.

Le même motif explicite avec deux ans donne deux ans. Il ne modifie ni les filtres de collecte ni la preuve de rattachement technique au trading. Aucun changement de schéma n'est nécessaire : le champ structuré existait déjà.

## Corpus Jump avant/après

Artifact : `data/discovery/lot12/2d6ba1702416.html` (JSON Greenhouse), SHA-256 `7ae8cfe810a1398e3289e800e55dc54b5209fd959d477a044ee2d64df515fb49`.

108 annonces brutes ; **25 retenues avant et après**. Trois annonces changent de minimum ou d'explication ; leur score final reste nul :

| Référence | Correction | Résultat |
| --- | --- | --- |
| 6172858 | Historique de codage `5+ year track record` désormais stocké comme minimum de 5 ans | Exclusion d'expérience ajoutée ; exclusion technique maintenue |
| 7767735 | Même formulation avec `2+ year track record` : minimum de 2 ans | Score inchangé ; aucune déduction de statut junior |
| 8105914 | `At least 2-5+ years` interprété avec borne inférieure 2 | Fausse exclusion de 5 ans retirée ; exclusion technique maintenue |

Preuves : `data/discovery/lot23/experience/before.json`, `after.json` et `comparison.json`. Le catalogue public recapturé au lot 23 possède exactement la même empreinte ; cette concordance est documentée par la validation de collecte distincte.

## Contrôle global sur 811 offres conservées

La comparaison en lecture seule avec les scores calculés avant modification trouve **8 changements** : sept intervalles, une préférence directement associée. Quatre scores finaux changent :

| Source / référence | Texte déterminant | Avant → après | Compatibilité junior après |
| --- | --- | --- | --- |
| Citi / 26960978 | `3-7+ years of experience` | 0 → 68 | 0 point : minimum 3 ans |
| Goldman Sachs / 170226 | `Minimum 3-5 years trading experience` | 74 → 66 | 0 point : minimum 3 ans désormais reconnu |
| UBS / 349001 | `3-7+ years of institutional equity trading experience` | 0 → 70 | 0 point : borne inférieure 3 ans |
| UBS / 348225 | `Preferably 7+ years ... work experience` | 0 → 57 | 5 points par défaut ; statut junior non affirmé |

Les quatre autres scores restent nuls grâce aux exclusions indépendantes : Jane Street 8687964002, Morgan Stanley JR038192, IMC 4704856101 et Jump 8105914. La détection Jump du champ structuré intervient à la lecture du catalogue ; le simple recalcul des anciens objets en base ne reconstitue pas ce champ. Le contrôle global de score et le contrôle du parseur sont donc complémentaires.

Preuve : `data/discovery/lot23/score-impact.json`. Cette mesure précède l'import éventuel des nouveaux objets Jump du lot. Aucun reclassement automatique en junior n'est ajouté.

## Vérification

43 nouveaux cas couvrent les bornes d'intervalles, tirets Unicode, minimums explicites, préférences attenantes, historique d'entreprise, phrases historiques de production et portée exacte du motif Jump. Les suites expérience, scoring et Greenhouse réunies passent : **191 tests**. Ruff et mypy passent sur les modules modifiés.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_experience_evidence.py tests/test_scoring.py tests/test_greenhouse_filtered.py
.venv/Scripts/python.exe -m ruff check src/trading_radar/scoring.py src/trading_radar/greenhouse_filtered.py tests/test_experience_evidence.py
.venv/Scripts/python.exe -m mypy src/trading_radar/scoring.py src/trading_radar/greenhouse_filtered.py
```

Les artifacts locaux sous `data/` sont ignorés par Git. Les tests synthétiques sont autonomes et n'exigent ni réseau ni base réelle.
