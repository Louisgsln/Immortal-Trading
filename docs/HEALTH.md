# Contrôle de santé local

```powershell
trading-radar health
trading-radar health --max-age-hours 48 --config-dir config
```

La commande produit un rapport JSON sans appel réseau, sans initialiser Telegram et sans créer ni migrer la base. Elle ouvre SQLite en lecture seule, avec `query_only`, et lit toutes les métriques dans une même transaction. Les transactions déjà validées dans le journal WAL sont incluses ; les écritures concurrentes postérieures au début de cette lecture ne mélangent pas les métriques.

Le contrôle vérifie le schéma courant, `quick_check` et les clés étrangères. Il consulte les dernières collectes réussies de chaque source **activée** et compte les alertes `unknown` et `sending`. La dernière ligne de `scan_runs` est exposée pour information, sans son contenu détaillé. La fraîcheur dépend du dernier succès de la source : une collecte récente avec zéro offre est saine, et une offre publiée longtemps auparavant ne rend pas la collecte périmée.

## Résultats et codes de sortie

| `status` | `ready` | Code | Interprétation |
| --- | --- | --- | --- |
| `healthy` | `true` | 0 | Base valide et toutes les sources activées récemment collectées. |
| `degraded` | `true` | 0 | Collecte encore fraîche mais dernier essai en échec, alertes à examiner, aucune source activée, ou date de dernière exécution invalide. |
| `critical` | `false` | 1 | Base absente, illisible, corrompue ou incompatible ; source activée jamais collectée, périmée ou avec une date invalide. |
| `critical` | `false` | 2 | Configuration illisible ou invalide (`error: invalid_configuration`). |

Les erreurs de syntaxe d'arguments sont traitées par Typer avant exécution et utilisent son affichage habituel avec le code 2. Les erreurs de configuration du contrôle utilisent le JSON décrit ci-dessus. Aucun chemin privé ni contenu brut des erreurs de configuration/SQLite n'est retourné.

Le seuil est de **24 heures** par défaut, strictement positif et au maximum de 87 600 heures. Une réussite datant exactement du seuil reste fraîche. Les dates de sources sans fuseau, illisibles ou dans le futur sont critiques. Un échec plus récent que le dernier succès donne `degraded` tant que ce succès reste frais, puis `critical` quand il dépasse le seuil. Les sources désactivées ou retirées de la configuration ne bloquent pas la santé.

## Premier démarrage et Docker

Un nouveau déploiement sans base ou sans premier succès pour chaque source activée n'est pas encore prêt : le contrôle retourne 1. Il ne lance pas de collecte pour corriger cet état. Le watcher doit finir ses premiers inventaires ; une source durablement inaccessible nécessite un diagnostic de configuration/collecteur. Une sauvegarde restaurée avec des observations anciennes reste critique jusqu'à de nouvelles collectes réussies.

Utiliser cette commande comme sonde avec un délai initial adapté à l'inventaire de toutes les sources. Le statut Docker `unhealthy` ne déclenche pas à lui seul un redémarrage automatique du conteneur. Cette sonde mesure la disponibilité des données ; elle ne prouve pas que le processus watcher tourne à cet instant, ni que le réseau ou Telegram est disponible. Les avertissements `degraded` restent visibles dans le JSON tout en laissant la sonde réussir.

## Intervenir

Pour conserver ces observations et comparer leur évolution, utiliser [monitor record/history/show](MONITORING.md). La commande `health` conserve son comportement de consultation seule.

- `database_missing` / `source_never_scanned` : attendre le premier inventaire ou vérifier la commande de démarrage, la configuration et le volume de données.
- `database_schema_incompatible` : vérifier la version de l'application ; `health` ne répare ni ne migre la base.
- `database_corrupt`, `database_integrity_failed`, `database_foreign_keys_failed` : examiner le stockage et utiliser la [restauration vérifiée](BACKUPS.md).
- `database_unreadable` : vérifier les permissions et la disponibilité du stockage ; un verrou SQLite peut aussi empêcher la lecture.
- `source_stale` / `source_recent_failure` : utiliser `trading-radar audit`, puis examiner les journaux de collecte.
- `alerts_need_review` : consulter `trading-radar alerts list` et le [guide des alertes](ALERTS.md). Le contrôle ne renvoie aucun message et ne modifie aucun statut.

Le contrôle ne prend pas le verrou applicatif du scanner et ne modifie pas les données, la configuration ou le mode de journalisation. SQLite conserve ses mécanismes normaux de coordination WAL ; le volume doit permettre la lecture des fichiers auxiliaires correspondants. Un contrôle de santé ne remplace pas une sauvegarde ni un exercice de restauration.
