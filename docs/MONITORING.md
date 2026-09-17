# Historique local de santé

`health` reste une inspection en lecture seule. `monitor record` enregistre, sur demande,
le même diagnostic dans un dossier séparé : `data/health-history` par défaut.
Ces commandes n'effectuent aucune collecte réseau, aucun envoi, aucune migration SQLite
et aucune planification. L'historique de santé ne remplace pas une sauvegarde métier.

## Enregistrer et consulter

```powershell
trading-radar monitor record
trading-radar monitor history
trading-radar monitor history --status critical --limit 20 --offset 0
trading-radar monitor history --since 2026-09-17T00:00:00+02:00 --until 2026-09-18T00:00:00+02:00
trading-radar monitor show IDENTIFIANT
```

`IDENTIFIANT` est le champ `id` renvoyé par `record` ou `history`. Il contient un horodatage
UTC précis à la microseconde et un UUID. `record` accepte `--config-dir`, `--history-dir`
et `--max-age-hours` (24 heures par défaut). `history` et `show` acceptent `--history-dir`
et consultent uniquement ce dossier : ils ne chargent pas la configuration ni la base.
Utiliser un dossier distinct pour chaque base et environnement, pour conserver des
comparaisons cohérentes. Les commandes ne sélectionnent jamais automatiquement une
autre base après une restauration.

Codes de sortie :

| Commande | 0 | 1 | 2 |
| --- | --- | --- | --- |
| `record` | Diagnostic sain ou dégradé enregistré | Diagnostic critique enregistré | Configuration, argument ou archivage invalide |
| `history` / `show` | Lecture et vérification réussies | — | Argument, fichier ou archive invalide |

Un code `1` de `record` est donc un diagnostic exploitable : le fichier est bien conservé.
Une base absente ou corrompue produit un rapport critique sans être créée ou réparée.
Le seuil de fraîcheur doit être strictement positif et ne pas dépasser 87 600 heures.

## Historique et comparaison

`history` renvoie `total`, `matching`, `limit`, `offset`, `snapshots` et
`latest_comparison`. La limite vaut 50 par défaut, entre 1 et 200 ; le décalage est
positif ou nul. Les dates de filtre sont des horodatages ISO 8601 avec fuseau, bornes
incluses. Les statuts acceptés sont `healthy`, `degraded` et `critical`.

Les rapports apparaissent du plus récent au plus ancien, puis par identifiant pour
départager deux captures au même instant. Les résumés contiennent le statut global,
la disponibilité, les compteurs de sources et les problèmes ; `show` rend le rapport
complet, avec l'enveloppe d'archivage et son empreinte.

`latest_comparison` compare les deux dernières observations de **tout le dossier**,
indépendamment des filtres et de la pagination. Il est nul avec moins de deux rapports.
Il expose le changement de statut global, les sources ajoutées ou retirées et les
changements de santé des sources : régression, amélioration ou changement de même gravité.
Une source retirée n'est pas considérée comme rétablie. `same_freshness_threshold`
indique si les deux rapports utilisaient le même seuil : un seuil différent peut expliquer
un changement de statut. Une comparaison décrit les observations, sans établir la cause
d'une dégradation. L'apparition ou la disparition de sources peut aussi provenir d'un
changement de configuration. Si l'une des bases n'a pas pu être inspectée,
`sources_comparable` vaut faux et `source_changes` reste vide : l'absence d'observation
ne permet pas de conclure que des sources ont été retirées. Le statut global reste comparé.

## Format et intégrité

Chaque fichier `<id>.json` contient une enveloppe de version `1` : `format_version`,
`id`, `recorded_at`, `report` et `sha256`. L'empreinte SHA-256 couvre l'enveloppe sans
le champ `sha256`, sérialisée en JSON UTF-8 avec clés triées et séparateurs compacts.
Elle détecte les changements accidentels ; elle ne constitue pas une signature contre
une personne capable de réécrire le fichier et son empreinte.

La publication écrit d'abord un fichier temporaire dans le même dossier, le vide sur
disque puis crée un lien dur vers le nom définitif. Le nom définitif n'apparaît qu'une
fois le JSON complet écrit et n'écrase jamais un rapport existant. Le système de fichiers
doit permettre les liens durs (notamment NTFS et les systèmes de fichiers Linux usuels).
Les captures concurrentes possèdent des identifiants distincts ; une collision échoue.
Le nettoyage retire le temporaire de cette invocation. Un temporaire laissé par un arrêt
brutal est ignoré par les lectures. La publication atomique évite un fichier partiel après
interruption du processus ; elle ne garantit pas à elle seule la durabilité du répertoire
après une panne matérielle.

`record` refuse un dossier confondu avec la base SQLite, son WAL, son SHM, son journal ou son verrou,
y compris un sous-dossier de ces chemins résolus. Les lectures refusent les identifiants
avec traversée de chemin, les fichiers liens symboliques, les versions inconnues, les
champs JSON dupliqués, les empreintes incorrectes et les fichiers dépassant 2 Mio.
`history` vérifie tous les JSON du dossier, même hors filtre : une corruption bloque la
consultation au lieu de masquer silencieusement un diagnostic. Conserver uniquement les
rapports de ce format dans le dossier.

L'application ne propose aucune modification ni suppression des rapports. Il n'y a ni
purge automatique, ni rétention configurée, ni service lancé en arrière-plan. Le dossier
peut être copié dans une sauvegarde locale selon les besoins ; aucune archive n'est envoyée.
