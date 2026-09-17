# Lot 33 — Reconnaissance junior DRW campus

Travaux du **17 septembre 2026**, avec deux sous-agents : helper de reconnaissance
DRW et revue indépendante des offres/régressions. L'agent principal a mesuré
l'impact, testé le parcours de correction et contrôlé sa persistance.

## Résultat

**DRW Floor Trader, Chicago, passe de 79 à 94.** L'indice junior est désormais
étayé par la catégorie employeur Campus, le contrat à temps plein et le critère
de diplôme attendu dans les exigences candidat. La composante junior passe de
5 à 20 ; toutes les autres composantes restent identiques.

- Offre officielle : [Floor Trader, 8207750](https://job-boards.greenhouse.io/drweng/jobs/8207750).
- Identité locale préservée : `bc7cb69d-4865-4a23-a82e-39bdc356d48e`.
- Début publié conservé : **Summer 2027**, sans date exacte inventée.
- Publication conservée : **16 septembre 2026, 22:00:49 UTC** ; deadline inconnue.

Les **813 autres offres stockées sont inchangées**. La base reste à **814 offres,
812 actives, 164 scores actifs ≥70 et 250 ≥55**, avec 46 scans métier. Le score
reflète le barème du projet, sans certifier l'éligibilité personnelle ni la
spécialisation du desk à partir du texte général de l'entreprise.

## Règle volontairement limitée

Le helper s'applique uniquement au connecteur DRW et exige :

1. La catégorie exacte `['Campus']` et le contrat exact `Full-time`.
2. Une rubrique candidat reconnue et unique, telle que `What you bring to the team`.
3. Une phrase de diplôme suivie d'une date de diplôme attendue entre deux mois/années,
   à l'intérieur du même bloc pertinent.
4. Aucune indication de stage ou apprentissage dans le titre ou le texte du rôle.

Les formulations facultatives, passées ou générales ne créent pas d'indice.
Les frontières HTML et les phrases limitent le rapprochement des termes. La
variante `graduating between` des deux offres Quantitative Trading Analyst reste
hors de cette nouvelle règle ; leur titre leur donne déjà le score junior adapté.
Les exclusions de séniorité et les minima d'expérience restent applicables.

La revue indépendante a détecté un défaut avant livraison : une rubrique
annonçant un stage après les exigences était hors du contrôle initial. La garde
de stage couvre désormais le texte du rôle jusqu'à l'introduction générale DRW,
indépendamment de la fin de la rubrique des exigences. Le contre-exemple dérive
d'un véritable stage DRW marqué `Full-time`.

Voir le corpus, les cinq offres Campus retenues et les limites dans
[DRW-CAMPUS-AUDIT-LOT33.md](DRW-CAMPUS-AUDIT-LOT33.md).

## Mesure, sauvegarde et application

La capture DRW du lot 32 a été réutilisée **hors réseau**, après contrôle SHA-256 :
154 annonces brutes, 27 retenues. La référence du parseur précédent a été produite
avec le paquet non éditable du lot 32, avant installation du correctif.

Une seule offre reçoit un nouvel indice et change de score dans le replay des
27 annonces comme dans la comparaison des 814 offres stockées. La correction
locale reprend uniquement l'indice démontré, puis recalcule le score sur l'objet
conservé. Elle ne réimporte pas la capture et ne simule pas une nouvelle observation.

- Sauvegarde vérifiée : `data/backups/lot33-before-drw-campus.zip`.
- Restauration dans `data/discovery/lot33/rehearsal.db` : onze tables identiques
  à la référence avant correction.
- Répétition puis application : une modification, une version `rescored` et une
  entrée de score ajoutées ; toutes les anciennes lignes d'historique conservées.
- **Huit tables intégralement préservées**, dont candidatures, alertes, sources
  et scans. Seuls les emplois, versions d'offres et scores changent.
- Pour l'offre corrigée, seuls `seniority_hint`, `seniority` et `score_breakdown`
  changent dans le payload ; le score SQL est synchronisé. Les dates de collecte,
  publication, début, première observation et modification restent identiques.
- Second passage : **zéro changement**. Aucun notifier construit ni alerte créée.
- CSV et dashboard actualisés ; identité et score 94 vérifiés dans les exports.

## Validation

- **1 958 tests réussis**, soit 70 nouveaux ; couverture Python **96 %**.
- 46 tests du helper, 22 régressions indépendantes via le collecteur et deux
  scénarios de preview/correction locale ; 88 tests Greenhouse existants conservés.
- Ruff : **152 fichiers** conformes ; mypy : **62 fichiers**, sans erreur.
- Paquet reconstruit hors réseau depuis `uv.lock`, suite complète sur installation
  non éditable. Aucune dépendance, migration ou configuration métier ajoutée.

Preuves locales sous `data/discovery/lot33/` : `before.json`, `parser-before.json`,
`impact.json`, `quality-audit.json`, `rehearsal.json`, `apply.json`, `exports.json`,
`test-results.xml` et `test-results.txt`. `workflow.py` conserve le déroulé ponctuel
et ses contrôles. Ces artefacts et la sauvegarde sont exclus du suivi Git.

Aucune collecte réseau, candidature envoyée, notification, surveillance ou
déploiement lancé. L'interface est inchangée ; aucune nouvelle inspection visuelle.
Les limites relatives aux rôles hybrides, aux mentions d'actifs dans les textes
généraux et à la validation Docker/VPS restent ouvertes.
