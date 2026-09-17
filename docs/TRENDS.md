# Tendances de l'activité observée

La commande `trends` résume l'historique local par jour UTC. Elle lit la base existante
sans collecter de nouvelles offres, lancer de watcher, modifier les candidatures ou
envoyer de notification.

```powershell
trading-radar trends
trading-radar trends --days 7
trading-radar trends --days 90 --config-dir config
```

La fenêtre vaut **30 jours par défaut**, de 1 à 365 jours. Elle comprend le jour UTC
en cours, jusqu'à l'instant de génération, et les jours précédents. Par exemple, un
rapport de 7 jours généré le 17 septembre à 14 h UTC commence le 11 septembre à 0 h UTC.
Le dernier jour est donc partiel. Les journées sans événement figurent avec des zéros.
Les enregistrements datés après l'instant de génération sont exclus des compteurs.

## Lire les compteurs

| Champ JSON | Signification |
| --- | --- |
| `new_jobs` | Offres dont la première détection locale (`first_seen`) tombe ce jour-là. |
| `updates` | Versions enregistrées avec l'événement `updated`. |
| `rescored` | Versions enregistrées après un nouveau calcul du score (`rescored`). |
| `closed` | Versions enregistrant une fermeture (`closed`). |
| `reopened` | Versions enregistrant une réouverture (`reopened`). |
| `scans` | Exécutions de collecte enregistrées, y compris celles ayant échoué et les imports locaux sans requête réseau. |
| `failed_sources` | Somme du nombre de sources en échec à chaque exécution enregistrée. |

**Première détection ne signifie pas publication.** L'initialisation d'une source ou un
import local peut faire découvrir aujourd'hui des offres publiées depuis longtemps.
La commande ne reconstitue pas une date de publication absente. Elle utilise la première
détection du poste canonique : une même offre reconnue sur plusieurs sources ne devient
pas plusieurs nouvelles offres.

Les mises à jour, recalculs, fermetures et réouvertures comptent des événements conservés,
pas une variation nette du nombre d'offres actives. Un poste fermé puis rouvert compte
une fermeture et une réouverture. Plusieurs événements du même poste peuvent être
comptés le même jour. `failed_sources` n'est pas un nombre d'employeurs uniques : deux
exécutions en échec sur la même source comptent deux occurrences.

## Format et erreurs

Le résultat JSON est écrit sur la sortie standard. Il comprend `status`, `error`,
`generated_at`, `timezone` (`UTC`), `days`, `window` (`start`, `end`), `daily` et `summary`.
Chaque élément de `daily` comprend `date` et les sept compteurs ci-dessus. `summary`
contient leurs sommes sur la fenêtre. Aucune description d'offre, note de candidature,
information de recruteur ou valeur de configuration n'est incluse.

- Code de sortie `0` : rapport complet disponible, y compris si tous les compteurs valent zéro.
- Code `1` : configuration indisponible, base absente, historique invalide ou lecture impossible.
- Code `2` : arguments de commande invalides, par exemple `--days 0` ou `--days 366`.

Une erreur de configuration produit un diagnostic `invalid_configuration` sans détails
sensibles. Une erreur de lecture renvoie `status: "error"`, un objet `error` avec un code
et un message, `daily: []` et `summary: {}`. Une lecture incomplète n'est pas présentée
comme un rapport partiel exploitable.

## Historique et limites

Les trois tables utiles (`jobs`, `job_versions`, `scan_runs`) sont lues dans une transaction
SQLite cohérente, en lecture seule. Le schéma courant est requis ; la commande ne crée
ni ne migre la base. Les données déjà validées dans le journal WAL sont prises en compte.

Le rapport dépend uniquement de l'historique conservé. Il ne reconstitue ni les anciennes
collectes absentes ni les versions supprimées. Les dates sont vérifiées dans tout l'historique,
même hors de la fenêtre demandée : réduire `--days` ne contourne donc pas des données
invalides plus anciennes. Les limites actuelles sont de **100 000 lignes par table** et
de **1 000 000 caractères de métriques par exécution**. Leur dépassement refuse le rapport
avec le code métier `limit_exceeded`, sans tronquer silencieusement les résultats.

Les codes métier possibles sont `missing`, `incompatible`, `corrupt`, `unreadable`,
`invalid_data`, `limit_exceeded` et `invalid_config`. Vérifier la configuration ou
restaurer une [sauvegarde vérifiée](BACKUPS.md) selon la cause ; la commande ne répare
pas automatiquement l'historique.

## Dans le dashboard

Le [dashboard local](DASHBOARD.md) embarque 90 jours d'activité et permet d'en afficher
7, 30 ou 90 jours sans requête réseau. Il conserve le comportement d'un instantané :
un nouvel export ou un redémarrage du serveur est nécessaire après une collecte.

Les tendances, les offres et le diagnostic de santé sont des lectures distinctes.
Pendant une collecte concurrente, leurs instants d'observation peuvent donc différer
légèrement. Les tendances ne remplacent pas le contrôle de santé actuel des sources.
Une indisponibilité des tendances est signalée sans empêcher la consultation des offres.
