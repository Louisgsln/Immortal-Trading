# Lot 81 — Énergie, matières premières et courtage

Trois portails Workday publics ajoutés après vérification du lien depuis le site
employeur. Le périmètre devient 43 sources et 38 employeurs.

| Employeur | Preuve officielle | Portail | Annonces dans la simulation |
| --- | --- | --- | ---: |
| BP | [Carrières](https://careers.bp.com/) — Candidate login | `bpinternational.wd3.myworkdayjobs.com/bpCareers` | 2 |
| Shell | [Carrières](https://www.shell.com/careers.html) — Search for a job | `shell.wd3.myworkdayjobs.com/ShellCareers` | 2 |
| TP ICAP | [Offres](https://tpicap.com/tpicap/careers/opportunities) — liens des fiches | `tp.wd107.myworkdayjobs.com/TP-ICAP` | 12 |

Recherches : `trading`, `trader`, `quantitative`, `structuring` et, pour TP ICAP,
`broker`. Intervalle de 30 minutes, deux secondes entre requêtes. Opérateurs,
conformité, support, infrastructure et intitulés seniors identifiés sont exclus
de ces recherches. Les programmes BP comportent des rotations commerciales et
opérationnelles : leur présence ne garantit pas une affectation de trader.

## Ciblage et fiches

Six annonces Trainee Broker TP ICAP comportent, dans une liste de missions
identifiée, soit des cotations et opportunités avec contact client, soit
l'introduction d'ordres client. Elles sont classées **BROKING**, avec 22/30 pour
la proximité du trading. La simple saisie ou réconciliation ne suffit pas.
Les classes d'actifs viennent de ces missions et du titre, pas de la présentation
générale du groupe. Trois brokers non qualifiés restent à zéro.

Algorithmic Trading Developer est reconnu grâce aux missions de stratégies et
d'implémentation avec les quants, sans requalification en débutant. Les exigences
d'expérience restent applicables. Stages, seniors et Associate seuls gardent
leurs exclusions ; Analyst/Associate reste autorisé.

Rubriques de missions TP ICAP/Shell et diplômes BP/Shell/TP ICAP ajoutées.
Conditions originales conservées ; les rubriques manquantes restent inconnues.
Recherches partielles : aucune clôture par absence. Les contrôles Workday de
pagination, titres et identifiants, robots et budgets restent appliqués.

## Mesure avant installation

Collecte réelle sur copie de 974 offres : 60 requêtes, 16 nouvelles offres,
13 pertinentes et 7 prioritaires ; 11 avec missions, 5 avec diplôme, 16 avec
publication. Les 974 scores existants sont inchangés, les suivis et historiques
sont préservés, aucune alerte ajoutée. Premier import en exploitation silencieux.
Installation le 26 septembre à 23:06 après sauvegarde vérifiée. Les trois sources
ont réussi leur première collecte automatique entre 23:06 et 23:07, après les
collectes réelles de préparation sur copie. Aucun test de message Telegram.

Contrôle à 23:10 : 990 offres, 295 pertinentes, 182 prioritaires ; 436 fiches
avec missions, 364 avec diplôme et 539 avec publication connue. 42/43 sources à
jour ; Nomura campus reste bloqué par CAPTCHA. Les 16 offres des nouveaux portails
correspondent aux identités publiques et scores de la simulation, sans alerte
créée pour ces sources. Les suivis, anciens scores et historiques sont conservés.

Le paquet installé (93 fichiers), le scanner actif, le dashboard et l'API de suivi
sont vérifiés. Le navigateur confirme les filtres, dates, fiches, explications
BROKING et l'historique de collecte, sans erreur JavaScript.

Validation locale : **3 988 tests réussis, 4 ignorés**, analyse statique de
88 modules, format et lint de 244 fichiers. Tous les
[contrôles GitHub du code livré](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36271763749)
sont réussis : Python 3.11–3.14, 11 tests JavaScript et construction/restauration
en conteneur. Les lots 79 et 80 ont également terminé leurs contrôles avec succès.

Trafigura, Vitol et Marex examinés mais non ajoutés : validation distincte de
leurs catalogues encore nécessaire. Aucun contournement d'accès.
