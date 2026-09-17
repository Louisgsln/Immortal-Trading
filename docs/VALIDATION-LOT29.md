# Lot 29 — Préférences et expérience ajoutée au diplôme

Travaux du **17 septembre 2026**, avec trois sous-agents : préférence directement
attachée, extraction additive au diplôme, régressions indépendantes. L'agent
principal a intégré les changements, comparé les 813 offres et effectué une
répétition avant le recalcul réel.

## Changements livrés

- `Experience Desirable:` directement attaché à une expression déjà reconnue
  n'est plus traité comme un minimum obligatoire. Le marqueur ne s'étend pas à
  une rubrique entière et ne supprime pas les exigences indépendantes.
- `degree … plus N years … experience` peut apporter un minimum additionnel,
  avec une grammaire bornée. Les préférences et alternatives ambiguës sont
  écartées de cette nouvelle extraction. Le texte brut conserve ses frontières
  et les bornes des intervalles avant la normalisation historique.
- `rescore` n'initialise plus Telegram lorsque les alertes sont configurées comme
  actives. Le recalcul fonctionne sans ses identifiants et n'envoie rien.

La revue indépendante a trouvé des alternatives `MSc`, `MBA` et `M.Sc.` qui
pouvaient transformer les sept années d'un parcours en minimum universel. Elles
sont désormais couvertes : un `or` hors de la portion du diplôme rend cette
nouvelle extraction ambiguë. Les alternatives de discipline et d'équivalence
étrangère restent admises dans la portion du diplôme.

La nouvelle règle n'annule aucun minimum trouvé par les expressions historiques.
Elle n'est pas une interprétation générale des alternatives diplôme/expérience.
Voir [DEGREE-EXPERIENCE-LOT29.md](DEGREE-EXPERIENCE-LOT29.md) et
[QUALIFICATION-REGRESSIONS-LOT29.md](QUALIFICATION-REGRESSIONS-LOT29.md).

## Effet mesuré sur les 813 offres

La référence a été calculée avec le paquet installé du lot 28, avant modification
du parseur source. Les descriptions ont gardé les mêmes empreintes. La préférence
a été mesurée seule, puis avec la nouvelle extraction additive :

| Offre | Minimum textuel avant → après | Score avant → après |
| --- | --- | --- |
| Crédit Agricole CIB — Analyst, Sales SLT & CRI Americas | `[1]` → `[]` | 82 → 82 |
| Susquehanna — Quant Developer, Trading Strategies, Experienced Hire | `[]` → `[7]` | 65 → 0 |

Le minimum structuré CA reste à zéro ; la préférence ne prouve aucune éligibilité.
Chez Susquehanna, le diplôme ou son équivalent étranger est suivi explicitement
de sept ans d'expérience. La substitution de l'éducation mentionnée ensuite
n'annule pas cette exigence. L'exclusion existante des minima d'au moins cinq ans
s'applique désormais ; le libellé `Experienced Hire` n'a pas été transformé en
règle numérique générale.

**Exactement deux listes d'expérience et un seul score changent.** La base reste
à **813 offres, 811 actives, 163 scores actifs ≥70** ; les scores actifs ≥55 passent
de **250 à 249**. Aucun autre score, explication ou classement ne change.

## Sauvegarde, répétition et application

- Sauvegarde vérifiée : `data/discovery/lot29/before-rescore.zip`, restaurée dans
  `rehearsal.db` pour la répétition.
- Sur la copie, puis sur la base réelle : un recalcul, une version `rescored` et
  une entrée d'historique de score. Second passage : **zéro changement**.
- Contenu exact des **huit tables non concernées** conservé : candidatures et
  historique, alertes et historique, sources, scans et version de schéma.
- Toutes les autres données des offres sont identiques, dont dates de collecte,
  première observation, date de modification et état actif. Les anciennes lignes
  des historiques de versions et scores sont conservées.
- Intégrité et relations SQLite valides. La base conserve 45 scans métier ; aucune
  collecte réseau, notification, candidature envoyée ou surveillance lancée.
- CSV de 813 lignes et export HTML actualisés, score Susquehanna à zéro vérifié
  dans les deux. Aperçu HTTP local : réponse 200. L'interface n'a pas changé et
  aucune nouvelle inspection visuelle n'est annoncée.

## Validation

- **1 779 tests réussis**, soit **115 nouveaux**, couverture Python **96 %**.
- 13 tests de préférence, 72 tests du helper additif, 29 régressions indépendantes
  et un parcours aperçu/application/répétition avec candidatures préservées et
  initialisation Telegram interdite, même avec les alertes activées.
- Ruff : **144 fichiers** conformes ; mypy : **60 fichiers**, sans erreur.
- Paquet reconstruit hors réseau depuis `uv.lock` et testé sans installation éditable.
  Après harmonisation des fins de ligne, reconstruction finale et **279 tests**
  expérience, score, aperçu et CLI réexécutés avec succès. Les trois modules
  modifiés correspondent exactement au paquet installé.
- Aucune dépendance, migration ou modification des fichiers synchronisés.

Preuves sous `data/discovery/lot29/` : `before.json`, `preference-impact.json`,
`final-impact.json`, `rehearsal.json`, `apply.json`, `exports.json`,
`tested-source.json`, `test-results.xml` et `test-results.txt`. Les scripts locaux
d'audit et de recalcul y conservent les contrôles exécutés ; ces artefacts sont
ignorés par Git.

## Suite

La portée générale des rubriques et les alternatives implicites restent à analyser
sur des exemples vérifiés. Les portails early careers et les filtres Citi plus
ciblés restent des pistes de couverture. La validation Docker/VPS et la copie
distante des sauvegardes demandent toujours un environnement adapté.
