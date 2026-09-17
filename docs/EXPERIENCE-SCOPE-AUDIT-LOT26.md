# Audit de portée des exigences d’expérience — lot 26

## Conclusion

Le corpus local contient **sept offres où `ideally` qualifie directement le nombre d’années**, mais où le parseur du lot 25 présente ce nombre comme une exigence. La correction justifiée consiste à reconnaître cette préférence locale, et à appliquer les marqueurs de préférence directement attachés aux trois motifs d’extraction existants.

Cela ne démontre pas que les postes sont juniors ou que le candidat est éligible. Une préférence d’expérience reste une information utile lors de la lecture de l’annonce. Les autres exclusions, indices employeur et composantes du score doivent rester applicables.

## Méthode et traçabilité

- Lecture des **813 offres** de `data/jobs.db` via SQLite `mode=ro`, `query_only=ON` et transaction de lecture ; aucune utilisation de `Repository` et aucune écriture dans la base.
- Analyse de `required_experience_years`, de ses tests existants et recherches ciblées dans `description_text` : préférences, rubriques de qualifications, alternatives diplôme/expérience et histoire de l’employeur.
- Résultats de référence calculés avec le **package installé du lot 25**, distinct du code source modifié en parallèle pour le lot 26. Au total, **197 offres** produisent au moins un minimum dans cette version.
- Preuve locale : [corpus-audit.json](../data/discovery/lot26/corpus-audit.json). Le fichier contient les minima des 813 offres, le hash du parseur de référence, le hash des données, et pour chaque cas sélectionné : ID, URL de candidature, identifiant externe, extrait exact avec offsets dans `description_text`, hash de la description et détail du score de référence.
- Les annonces n’ont pas été revérifiées sur le réseau. Les extraits sont ceux de la collecte déjà conservée localement.

## Sept préférences directement attachées

| Entreprise et offre | ID local | Extrait exact déterminant | Minimum lot 25 | Score lot 25 |
| --- | --- | --- | --- | --- |
| Jane Street — Data Center Engineer | `0d0a7ef1-f6c1-4bfe-9b7e-ff7c14d7e6fe` | `Ideally 5+ years of experience working in a data center environment` | 5 | 0 |
| Jane Street — Data Centre Engineer | `30aa8007-a57c-4408-a65a-fa86c5419e22` | `Ideally 5+ years of experience working in a data centre environment` | 5 | 0 |
| Jane Street — Data Centre Engineer | `ed54e007-ee9b-48ba-837b-0215735bdd8a` | `Ideally 5+ years of experience working in a data centre environment` | 5 | 0 |
| Morgan Stanley — Global Capital Markets Roadshow Coordinator | `5a45a770-75e7-48f8-8533-33ccd30d6b9d` | `Skills Required Ideally 3+ years of corporate experience` | 3 | 0 |
| UBS — Electronic Trading Quantitative Analyst | `c3c88d9f-3bb0-414d-9f89-7fa589b0c5c9` | `ideally 2+ years of experience with Algorithmic Trading Strategies` | 2 | 92 |
| UBS — ETF Capital Markets Specialist | `f69f31eb-efb3-48c2-948b-958aba2504f4` | `ideally 7+ years’ experience in asset management or related passive investments field.` | 7 | 0 |
| UBS — Execution Trader, Asset Management | `64264ae3-73b9-4fd4-980b-312f2e07063b` | `ideally 3-7+ years of institutional equity trading experience` | 3 | 70 |

Ces sept descriptions ne contiennent pas d’autre minimum reconnu par le parseur lot 25. Le résultat attendu de l’extraction après cette correction locale est donc une liste vide. Cette attente ne concerne pas les éventuels minima structurés de l’employeur, ni les autres règles de score.

## Rubriques et limites

Deux cas Goldman Sachs présentent un marqueur de rubrique immédiatement avant le motif :

- `c40698a3-52eb-4156-9fe8-116cb6ce05a7`, Quant Coverage Associate Hong Kong : `PREFERRED QUALIFICATIONS Minimum of 1 year work experience in Equities` ; sortie lot 25 `[1]`, score 78.
- `b6bc3c34-806d-4e6d-b01c-c608ed172a80`, Prime Margin Lending Analyst Hyderabad : `Preferred Qualifications • At least 2 years of experience in Operations or related field` ; sortie lot 25 `[2]`, score 0.

Ces deux exemples peuvent bénéficier de la correction du marqueur directement attaché. Ils ne justifient pas une propagation générale de la préférence à toute la rubrique : le texte normalisé a perdu une partie de la structure HTML et des limites entre listes.

Un autre cas reste hors du périmètre retenu : Crédit Agricole CIB, `6b436a14-8f02-4846-b09d-c217a0422f1a`, `Experience Desirable: 1+ years of relevant experience in banking, preferably in Project Finance and Digital Infrastructure` ; sortie lot 25 `[1]`, score 82. La reconnaissance des intitulés de rubriques et de leur portée nécessite un traitement distinct.

La recherche ciblée n’a pas identifié de faux minimum concret dû à une alternative diplôme/expérience, ni à l’histoire de l’employeur. Elle ne prouve pas leur absence exhaustive. Les exemples synthétiques correspondants ne doivent pas servir à annoncer un effet mesuré sur ce corpus.

## Contre-exemples à conserver

Une préférence sur le domaine ou le diplôme ne doit pas annuler une exigence d’expérience indépendante :

- **Macquarie Electronic Sales Trader**, `adb32e56-b87c-4147-981d-ef468df63f69` : `Strong academic background, ideally in finance, economics or a quantitative discipline 5+ years of relevant experience` → conserver `[5]`.
- **Société Générale FIC Derivatives Structurer**, `476a02fc-6c30-402a-a06f-62790d1018c7` : `You have at least 3 years of experience in financial markets, ideally gained within a structuring, pricing, trading or derivatives sales team.` → conserver `[3]`.
- **Goldman Sachs Site Reliability Engineer**, `549bfc95-f61d-4cc6-b31f-082f8e02b2dc` : diplôme `is a plus. At least 4 years of professional experience` → conserver `[4]`.
- **BNP Paribas UFT Automation Tester**, `e84ed201-1f55-45ac-9b55-3c6521db32a7` : `NICE to have experience in areas of API or Mobile Test Automation Specific Qualifications: • Minimum 5 years of experience in Automation Testing` → conserver les exigences `[5, 2]` de l’annonce.
- **Nomura US Trading Tools Development Lead**, `fa0eafa1-3a83-4c87-99e9-59c92cf34f0e` : `5+ years experience in financial services technology, preferably in trading or prime services` → conserver `[5]`.
- **Jane Street Campus Recruiter**, `1d21c2bb-7941-4da2-adca-3eade46f4e03` : histoire de recrutement `Over the past 25 years`, puis exigence candidat `Have 8+ years of university recruiting experience` → conserver `[8]`, sans ajouter 25.

## Vérification de l’impact

Comparer les 813 résultats avant/après, y compris les exclusions et raisons qui peuvent changer sans modifier le score total. Une première variante de travail séparait toutes les phrases avant extraction. L’audit a identifié deux écarts supplémentaires, **rejetés avant livraison** pour maintenir le périmètre de la correction :

- Citi Softs and Agricultural Commodities Trader, `3f75b37e-da3f-4019-b1e9-860410404625` : `Undergraduate degree required. 5–10 years of experience trading softs and/or agricultural commodities.`
- Goldman Sachs Risk and Control Self-Assessment Management Associate Dallas, `5f1fe210-182f-47fa-bb58-ed3e464e8f3b` : `experience within a risk management or control discipline context are required. 3+ years in the Financial Services / Banking industry`.

Le mot `required` appartient à la phrase précédente dans ces deux cas. La séparation supprimait aussi le résultat lié à une expérience réellement mentionnée : `[5]` pour Citi et `[3]` pour Goldman Sachs. La décision retenue est de conserver ces résultats historiques dans ce lot ; ces deux suppressions ne font pas partie de la correction livrée. Une amélioration future de la segmentation devra également reconnaître ces formulations d’expérience et mesurer son impact séparément.
