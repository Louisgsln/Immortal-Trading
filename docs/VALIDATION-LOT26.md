# Validation du lot 26 — Préférences d'expérience et aperçu du recalcul

17 septembre 2026, Windows, Python 3.14.3. Deux sous-agents ont réalisé l'audit du
corpus et le correctif du parseur. L'agent principal a ajouté l'aperçu de recalcul,
mesuré les impacts, répété puis appliqué les changements.

## Résultat mesuré

Les 813 offres conservées ont été comparées aux règles du lot 25. **Neuf extractions
de minima changent** : sept préférences `ideally` et deux marqueurs de préférence
Goldman Sachs directement attachés à une durée. La correction s'applique aux trois
motifs d'expérience historiques. Les minima structurés, les titres et les exclusions
indépendantes restent applicables.

**Six fiches ont un score détaillé ou une explication modifiés** :

| Offre | Total avant → après |
| --- | ---: |
| UBS — Execution Trader, Asset Management | 70 → 75 |
| UBS — ETF Capital Markets Specialist | 0 → 0 |
| Jane Street — Data Center/Centre Engineer, trois fiches | 0 → 0 |
| Morgan Stanley — Global Capital Markets Roadshow Coordinator | 0 → 0 |

Le poste Execution Trader conserve un niveau inconnu et les cinq points par défaut
de compatibilité junior ; cette correction ne déclare pas le poste junior ni le
candidat éligible. Les cinq autres fiches restent exclues par des critères indépendants.
Les trois extractions restantes portaient sur un ou deux ans et ne changent pas le score.

La base reste à **813 offres, 811 actives, 163 scores actifs ≥70 et 250 ≥55**.
Une première variante retirait aussi deux minima Citi/Goldman Sachs en séparant les
phrases. La revue l'a écartée : la détection historique est conservée, les limites
de phrase servent uniquement à borner la portée d'une préférence. Détails et preuves
dans [l'audit du corpus](EXPERIENCE-SCOPE-AUDIT-LOT26.md).

## Aperçu sans écriture

`trading-radar rescore --dry-run` expose les scores, explications et classifications
avant/après, ainsi que les effectifs aux seuils de pertinence et de priorité.
Il lit un instantané SQLite sans création, migration, historique, export CSV ou
initialisation de notifications. Une erreur refuse le rapport entier. Le guide
[SCORING-AUDIT.md](SCORING-AUDIT.md) précise les limites et l'application ultérieure.

## Répétition, application et préservation

- Sauvegarde vérifiée : `data/discovery/lot26/before-rescore.zip`, restaurée dans
  `rehearsal.db` pour la répétition.
- Sur la copie puis sur la base réelle : exactement six recalculs, chacun avec
  une entrée `rescored` et une entrée d'historique de score. Second passage : zéro changement.
- Contenu exact et empreintes des huit autres tables préservés : candidatures et
  historique, alertes et historique, sources, scans et version de schéma.
- Les autres champs des offres, notamment premières/dernières observations et
  date de modification, sont identiques. Contrôles d'intégrité et relations valides.
- Aperçu après application : zéro différence. CSV de 813 lignes et HTML régénérés.
- Export autonome contrôlé : score UBS 75, 115 recalculs historiques et toujours
  45 scans. Il reste en lecture seule. Serveur local relancé en mode édition, réponse
  HTTP 200 vérifiée ; l'ouverture du panneau navigateur a été demandée à l'application.

Le contrôle interactif du navigateur n'était pas disponible dans cette session.
Les assets visuels et le formulaire n'ont pas changé ; leur validation visuelle et
fonctionnelle du lot 25 reste documentée séparément. Le contenu du nouvel export a
été vérifié directement, sans annoncer une nouvelle inspection visuelle.

## Tests

- **1 517 tests réussis**, soit 58 supplémentaires ; couverture Python **96 %**.
- 38 nouveaux cas de portée des préférences, dont les gardes Citi/Goldman Sachs ;
  20 tests d'aperçu, limites, erreurs, WAL, concurrence et absence d'écriture.
- Ruff : **131 fichiers** conformes ; mypy : **56 fichiers**, sans erreur.
- Paquet reconstruit hors réseau depuis le lock et testé sans installation éditable.
  Après harmonisation de fins de ligne, les 61 tests expérience/aperçu/CLI concernés
  ont été réexécutés sur le paquet final avec succès.

Preuves sous `data/discovery/lot26/` : `before.json`, `corpus-audit.json`,
`minima-impact.json`, `score-impact.json`, `cli-preview.json`, `rehearsal.json`,
`apply.json`, `after-audit.json`, `preservation.json`, `test-results.xml` et
`test-results.txt`. Les fichiers sous `data/` sont ignorés par Git.

Aucune collecte réseau, candidature envoyée, notification ni automatisation lancée.
Pas de nouvelle dépendance, migration ou modification de `sources/`. Les alternatives
diplôme/expérience, la portée de rubriques complètes et les préférences éloignées
restent à traiter ; le lot ne prétend pas comprendre toutes les formulations.
