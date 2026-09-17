# Prévisualiser un recalcul des scores

Avant de recalculer les offres conservées avec les règles actuelles :

```powershell
trading-radar rescore --dry-run
trading-radar rescore --dry-run --config-dir config
trading-radar rescore --dry-run --demo
```

Cette commande lit la base existante dans une transaction SQLite et calcule les
scores en mémoire. Elle ne crée ni ne migre de base, ne modifie aucun historique,
n'exporte pas de CSV et n'initialise aucun transport de notification. La variante
`--demo` consulte uniquement la base synthétique existante `data/demo.db`.

## Lire le rapport JSON

- `evaluated` : nombre d'offres examinées, actives ou inactives.
- `changed` : offres dont le score détaillé, les explications, les catégories de
  poste ou les classes d'actifs seraient modifiés par `rescore`.
- `score_changed` : parmi ces offres, celles dont le total numérique change.
- `before` et `after` : totaux actuels et projetés, avec offres actives et seuils
  de pertinence ≥55 et de priorité ≥70, appliqués aux offres actives.
- `changes` : identifiants, titres et employeurs, puis scores, explications et
  classifications avant/après. Une modification d'explication peut conserver le
  même total, notamment si une autre exclusion reste valable.

Les descriptions intégrales, notes de candidature et contacts ne sont pas inclus.
Un score est un outil de classement ; il ne prouve pas l'éligibilité au poste.
Une préférence d'expérience ne constitue pas une preuve de niveau junior.

## Appliquer après examen

```powershell
# Choisir un nouveau nom d'archive.
trading-radar backup create data/backups/avant-recalcul.zip
trading-radar backup verify data/backups/avant-recalcul.zip
trading-radar rescore
```

Le rapport est un aperçu à un instant donné, pas une validation réutilisable pour
une écriture ultérieure : les données ou les règles peuvent changer entre les
commandes. `rescore` sans `--dry-run` recalcule toutes les offres avec les règles
alors présentes et historise les changements effectifs. Le recalcul conserve les
dates de collecte, l'état des sources et les candidatures ; il ne déclenche pas
de nouvelle collecte. Il rafraîchit le CSV. Recharger le dashboard éditable ou
recréer l'export HTML pour consulter les nouveaux scores.

Le recalcul et son aperçu n'initialisent pas Telegram, même si les alertes sont
activées dans la configuration : ils ne nécessitent pas ses identifiants.

Depuis le lot 29, `Experience Desirable:` directement attaché à une exigence
reconnue est une préférence. Les formulations explicites
`degree … plus N years … experience` apportent un minimum additionnel lorsque
la proposition n'est pas ambiguë. Les alternatives et préférences restent
traitées prudemment ; voir [le périmètre et ses limites](DEGREE-EXPERIENCE-LOT29.md).

## Erreurs et limites

Depuis le lot 34, deux passages exacts de présentation de DRW sont écartés de
la vue de texte servant aux actifs et aux termes de profil. Le titre et les
missions avant/après restent pris en compte ; les descriptions stockées et les
autres composantes du score sont conservées. Une explication indique ce retrait.
Le filtre vise uniquement les offres officielles de la source `drw` et ne
reconnaît pas toute formulation générique possible. `UNKNOWN` signifie absence
de terme reconnu dans cette vue, pas absence de marché traité par le poste.
Voir [l'audit et les contre-exemples](DRW-EVIDENCE-AUDIT-LOT34.md).

Code de sortie `0` : aperçu complet, y compris sans changement. Code `1` : erreur
de configuration, base absente/incompatible/corrompue, données incohérentes ou
limite dépassée. Le rapport d'erreur a `status: "error"`, `changes: []` et des
résumés vides ; il ne présente pas de comparaison partielle.

La lecture est limitée à **5 000 offres** et **2 000 000 caractères de payload par
offre**. La base doit avoir le schéma courant. Les données déjà validées dans le
journal WAL sont prises en compte. Les accès restent en lecture seule, même si
les alertes sont activées dans la configuration.
