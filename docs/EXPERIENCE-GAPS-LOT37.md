# Lacunes de lecture de l’expérience — audit indépendant du lot 37

## Résultat

Parmi les **250 offres actives de score ≥55**, **41** contiennent une fourchette numérique d’années. **30** de ces offres ne disposent d’aucun minimum reconnu dans le texte ou le champ structuré. Ces 30 cas ne sont pas tous des exigences : les préférences et profils habituels doivent rester distincts.

Le défaut vérifié est précis : le parseur réduit une fourchette à sa borne basse, puis ne reconnaît pas cette borne lorsqu’elle ne comporte ni `+`, ni marqueur obligatoire déjà pris en charge. Une correction bornée peut reconnaître les fourchettes associées explicitement à l’expérience personnelle, en préservant les préférences et alternatives.

## Dix cas de contrôle

Les attentes ci-dessous constituent les observations avant correction, pas une décision d’éligibilité. Au début du lot, dans les dix cas, le parseur renvoyait `[]`, le champ structuré était nul et le dashboard affichait `unspecified`. La correction et ses résultats sont décrits dans [VALIDATION-LOT37.md](VALIDATION-LOT37.md).

| Entreprise / titre | Score | Fourchette | Minimum attendu | ID local |
| --- | ---: | --- | --- | --- |
| citi — markets analyst equity trading | 84 | 6-10 years | 6 | `d7e09926-d2da-4c79-ad19-d016cc824e79` |
| citi — corporate structurer | 65 | 6-12 years | 6 | `726eed3f-b19e-4d2d-a7d8-b4da31611cbf` |
| citi — business execution principal trading | 57 | 6-10 years | 6 | `29fac7f5-3a06-4889-a0e5-f36d3e98bc21` |
| jane street — exotic options trader | 75 | 3-6 years | 3 | `0187a34e-5247-474a-a125-385b8ded5b4b` |
| citi — etrading java developer front office trading | 61 | 3-7 years | 3 | `44a344f0-c80b-4805-abba-f930bb54aeb1` |
| societe generale — junior fx em trader analyst | 94 | 1-3 years | 1 | `9f084f59-f85d-41e5-b81a-797baf656965` |
| drw — quantitative trading analyst | 92 | 1–2 years | 1 | `a456b41d-50b7-47c8-9b52-c2c0334d7a6a` |
| goldman sachs — trading desk strategist global banking and markets synthetic products group spg | 75 | 1 - 5 years | Non obligatoire / ne pas inférer | `18287b76-360e-4415-83e3-0649876c5c36` |
| citi — fx options trader | 69 | 3-7 years | Non obligatoire / ne pas inférer | `7d70d78e-8b4b-4bd7-a7c8-d659bbd9ccd1` |
| optiver — digital assets trader crypto options | 71 | 3-4 years | Non obligatoire / ne pas inférer | `25012ba7-399b-44d5-9aad-ab96c0ff3d76` |

## Limites à conserver

- **Borne basse uniquement.** `6-10 years` donne six, jamais dix. Une borne basse deux ne garantit pas qu’un candidat de deux ans sera retenu.
- **Préférences locales.** `1 - 5 years of work experience is preferable` doit rester facultatif. À l’inverse, `sales or trading functions preferred` après un point-virgule peut qualifier seulement le domaine, sans rendre facultatifs les `1-3 years relevant experience` précédents.
- **Titres de section.** `Recommended Qualifications: 3-7 years…` reste une recommandation. Ce marqueur doit être contrôlé avant d’élargir la reconnaissance.
- **Profil usuel.** `Typically 3-4 years…` ne constitue pas un minimum obligatoire ferme.
- **Alternatives et âge de société.** Préserver les branches diplôme/expérience, fourchettes inversées et phrases parlant de l’ancienneté de la société.
- **Phrases sans experience.** Ne pas ouvrir indistinctement tous les `N-M years in/of…`. L’exemple Jump `3–6 years in buy/sell-side research…` connu du lot 35 est hors de la population score ≥55 et nécessite une décision de portée séparée.

## Preuves et méthode

Lecture SQLite de la seule table `jobs`, URI `mode=ro`, `PRAGMA query_only=ON`, transaction de lecture. Aucun Repository, appel réseau, rescoring ou accès aux tables de candidatures. Aucun changement du code ou de la base.

[experience-gap-audit.json](../data/discovery/lot37/experience-gap-audit.json) contient les dix IDs, scores, résultats du helper avant correction, extraits originaux, offsets Unicode (base zéro, fin exclusive), hash SHA-256 de chaque description et payload, ainsi que le hash ordonné des 814 lignes de `jobs`.

Les extraits, offsets et hashes permettent de vérifier les constats sans republier les descriptions complètes. Les compteurs décrivent le corpus local observé, pas l’état actuel des sites carrières.
