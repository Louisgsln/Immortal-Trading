# Lot 37 — Fourchettes d’expérience sans signe « + »

Travaux du **17 septembre 2026**, avec trois sous-agents : audit et régressions
indépendantes, helper d’extraction, audit des rôles hybrides puis revue des impacts.
L’agent principal a intégré, mesuré, sauvegardé, répété et appliqué le recalcul.

## Résultat

Le parseur reconnaît désormais certaines fourchettes explicites associées à
l’expérience du candidat, comme `6-10 years of experience`, même sans signe `+`.
Il conserve la **borne basse**, le contexte des qualifications et les limites
de portée. **32 extractions changent sur 814 offres** ; **15 explications de score**
sont actualisées, dont **sept scores totaux** :

| Entreprise / offre | Minimum reconnu | Score avant → après |
| --- | ---: | ---: |
| Citi — Markets Analyst - Equity Trading | 6 | 84 → 0 |
| Citi — Trader - Equity Principal Trading | 6 | 67 → 0 |
| Citi — Corporate Structurer | 6 | 65 → 0 |
| Citi — Business Execution - Principal Trading | 6 | 57 → 0 |
| Jane Street — Exotic Options Trader, première offre | 3 | 75 → 70 |
| Jane Street — Exotic Options Trader, deuxième offre | 3 | 73 → 68 |
| Citi — eTrading Java Developer, Front Office Trading | 3 | 61 → 56 |

Le barème existant reste identique : au-delà de deux ans, la composante junior
devient nulle ; à partir de cinq ans, l’offre est exclue du classement ciblé.
La pertinence métier peut donc encore laisser une offre à 70 malgré trois ans
demandés. L’indicateur d’expérience du dashboard explicite cette différence.

Base finale : **814 offres, 812 actives, 161 prioritaires ≥70 et 246 pertinentes ≥55**.
DRW Floor Trader conserve **82**, son indice junior et l’absence de minimum chiffré.

| Catégorie d’expérience, offres actives | Avant | Après |
| --- | ---: | ---: |
| Minimum 0–2 ans | 55 | 71 |
| Minimum >2 ans | 163 | 178 |
| Minimum non reconnu | 594 | 563 |

## Périmètre et garde-fous

- Nouveau helper sur texte original ; les anciens patterns du parseur sont conservés.
- Fourchettes numériques simples avec `years` et `experience`, associées à des
  rubriques candidat reconnues, formulations directes ou début de clause explicite.
- Rubriques recommandées/préférées, préférences attachées, profils `Typically`,
  négations, bornes maximales et ancienneté de l’entreprise écartés.
- Alternatives académiques conservées. Une rubrique Education ultérieure ne fait
  pas disparaître un minimum d’expérience indépendant dans les qualifications.
- Bornes inversées, décimales partielles et nombres signés refusés.
- Aucun zéro inventé : seules les bornes basses explicitement écrites sont reconnues.

Cette règle conservatrice ne couvre pas toutes les langues ou structures HTML.
Les descriptions aplaties reposent sur un ensemble borné de débuts de rubriques
et d’items ; les formulations inconnues restent non reconnues. Les variantes
`years in…` sans le mot `experience`, notamment Jump Research Analyst, ne sont
pas ajoutées dans ce lot. « Non reconnu » ne signifie pas absence d’exigence.

L’[audit des lacunes](EXPERIENCE-GAPS-LOT37.md) documente dix cas et leurs preuves.
La revue indépendante des **32 changements**, avec contexte élargi et empreintes
des descriptions, n’a relevé aucun blocage avant application.

## Rôles hybrides : exclusions préservées

L’[audit parallèle](HYBRID-ROLE-AUDIT-LOT37.md) examine sept cas IMC, Jump, Jane Street
et XTX. Il ne justifie pas de lever les exclusions des rôles orientés production
et support. Jump Research Analyst associe des missions de trading à une fourchette
3–6 ans encore non reconnue ; un autre Research Analyst Jane Street décrit un stage.
Ces preuves restent des contraintes pour une future qualification métier conjointe.
Aucune règle de classification métier n’a changé ici.

## Application contrôlée

- Référence avant correction prise avec le paquet installé du lot 36.
- Sauvegarde `data/backups/lot37-before-experience-ranges.zip`, restaurée vers une copie
  distincte ; onze tables initialement identiques à la base active.
- Répétition puis application liée à l’empreinte de l’impact revu : **15 recalculs**,
  quinze versions et quinze événements de score ajoutés.
- **Huit tables intégralement préservées** ; dans les offres, seuls le score SQL et
  `score_breakdown` changent. **799 lignes d’offres entièrement inchangées**.
- Descriptions, métadonnées, dates de collecte et état actif préservés pour toutes
  les offres. Toujours 46 scans, aucun envoi d’alerte ou candidature.
- Second passage : **zéro modification**. Contrôles SQLite et clés étrangères valides.
- CSV et HTML réexportés ; scores des 814 offres et indications HTML comparés à la base.

## Validation

- **2 152 tests réussis**, soit **84 nouveaux**, couverture **96 %** sous Windows.
- 65 tests du helper et de son intégration ; 19 régressions indépendantes issues
  des cas audités, avec blocs Citi complets jusqu’à Education.
- Installation non éditable reconstruite hors réseau depuis `uv.lock`.
- Ruff : **162 fichiers** ; mypy : **65 fichiers**, sans erreur.
- Edge headless : compteurs et trois catégories, score ≥70, recherche et fiche Citi
  à six ans/score zéro, Floor Trader à 82 ; contrôles réussis sur HTML et serveur local.
- Aucune erreur JavaScript ; capture de la fiche inspectée. Le serveur a été remplacé
  pour charger le nouveau helper après vérification de ses processus.

Le [run Linux/Docker](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35205482883)
du commit `0c79786` a réussi sur ses **cinq jobs** : 2 152 tests sur chaque version
Python 3.11, 3.12, 3.13 et 3.14 sous Ubuntu, couverture 96 %, puis build, ENTRYPOINT
et reprise Docker. Le rapport conteneur confirme UID 10001 et onze tables identiques
après restauration. Les rapports JUnit et preuves Docker sont conservés par la CI.

## Preuves locales

Dans `data/discovery/lot37/` : `before.json`, `before-jobs.json`, audits avec offsets
et hashes, `impact.json`, `impact-review.json`, `rehearsal.json`, `apply.json`,
`post-apply-rescore.json`, `tests.txt`, `tests.xml`, `exports-verified.json`,
`ui-results.json` et captures. Les scripts `measure.py` et `workflow.py` conservent
les assertions de portée, de restauration et de préservation. Ces artefacts sont
ignorés par Git ; le dépôt public conserve le code, les tests et ce bilan.

Le premier contrôle du serveur a encore lu l’ancienne instance après un échec
d’arrêt PowerShell ; celle-ci a été arrêtée, les processus revérifiés et les deux
parcours navigateur relancés avec succès.
