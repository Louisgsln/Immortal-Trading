# Plan de conservation des sauvegardes

`backup plan` vérifie les sauvegardes locales et propose lesquelles conserver. La
commande ne supprime ni ne déplace aucun fichier. Elle ne lit pas la configuration
du radar, n'ouvre pas la base active et n'initialise aucun service de notification.
Elle fonctionne hors ligne, y compris depuis un autre répertoire que le projet.

```powershell
trading-radar backup plan data/backups
trading-radar backup plan data/backups --keep-latest 7 --keep-daily 14 --keep-weekly 8 --json
```

Les chemins relatifs sont résolus depuis le répertoire courant. Le répertoire
doit déjà exister. Il n'y a ni option `--apply`, ni tâche planifiée, ni stockage
distant associé à cette commande.

## Politique de conservation

Une archive est conservée dès qu'au moins une des trois règles la sélectionne.
Les règles s'ajoutent : les nombres ne sont pas des quotas exclusifs et leur somme
n'est pas le nombre de fichiers à conserver.

| Option | Défaut | Bornes | Règle |
| --- | --- | --- | --- |
| `--keep-latest` | 7 | 1 à 100 | Conserver les N sauvegardes les plus récentes. |
| `--keep-daily` | 14 | 0 à 365 | Conserver la plus récente de chaque jour UTC parmi les N derniers jours calendaires, aujourd'hui inclus. |
| `--keep-weekly` | 8 | 0 à 104 | Conserver la plus récente de chaque semaine ISO parmi les N dernières semaines, semaine courante incluse. |

Un jour ou une semaine sans sauvegarde reste vide : la fenêtre n'est pas prolongée
pour atteindre un quota. `0` désactive la règle quotidienne ou hebdomadaire. La
règle des sauvegardes les plus récentes reste toujours active.

L'ordre repose sur `created_at` dans le manifeste validé de l'archive, converti en
UTC, et non sur le nom du fichier ou sa date de modification. Une date absente,
invalide ou future bloque la recommandation pour cet audit.

## Vérification et limites

L'audit considère uniquement les entrées portant l'extension `.zip` (sans
distinction de casse) directement présentes dans le répertoire, sans parcourir
les sous-répertoires. Une entrée qui n'est pas un fichier ordinaire est invalide.
Il vérifie le contenu de chaque
sauvegarde avec le même contrôle que `backup verify` : manifeste, empreinte de la
base, schéma SQLite, intégrité et références entre tables. Une simple extension
`.zip` ne suffit pas à rendre une archive valide.

Les limites sont de **100 archives**, **512 Mio par fichier** et **2 Gio au total**.
Un dépassement produit un échec explicite ; il ne donne pas un plan fondé sur un
sous-ensemble silencieusement tronqué. Les chemins dangereux et les archives
modifiées pendant la vérification sont également refusés.

Si une archive est invalide ou illisible, le rapport prend le statut `blocked`.
Les archives valides sont toutes conservées : aucune recommandation
de suppression n'est produite sur un ensemble incomplet. Les autres fichiers du
répertoire ne deviennent jamais candidats.

## Lire le résultat

La sortie humaine indique les fichiers, leur décision et les motifs :

- `keep` : conserver ; motifs `latest`, `daily` et/ou `weekly`, ou
  `retained_due_to_incomplete_audit` si une autre archive empêche de finir l'audit.
- `candidate` : hors des trois règles ; motif `outside_retention`.
- `blocked` : archive invalide ; motif `invalid_archive` et code d'erreur associé.

Un candidat est seulement une proposition à examiner. Le plan n'est pas une
garantie future : le répertoire et les archives peuvent changer après l'audit.
Aucune suppression n'est implémentée, même si le rapport est valide.

Avec `--json`, la commande restitue exactement le rapport du moteur :

- `format_version`, `generated_at`, `directory`, `policy`, `status` ;
- `entries`, avec nom, taille, état, date et empreinte si disponibles, décision,
  motifs et éventuel code d'erreur expurgé ;
- `summary`, avec nombres d'archives valides, invalides, conservées et candidates,
  taille totale et taille des candidats ;
- `deletion_performed`, toujours `false`.

Le code de sortie vaut `0` pour un audit `ok` ou un répertoire `empty`, `1` pour un
audit `blocked` ou une erreur fatale, et `2` pour des arguments CLI invalides. Un
rapport bloqué est quand même imprimé. Une erreur fatale produit uniquement un
message court sur la sortie d'erreur, sans détail brut de l'exception.

## Conservation et récupération

La commande ne crée pas de sauvegarde. Utiliser les commandes existantes pour
produire un nouvel instantané et tester une récupération vers un fichier neuf :

```powershell
trading-radar backup create data/backups/radar-2026-09-17.zip
trading-radar backup verify data/backups/radar-2026-09-17.zip
trading-radar backup restore data/backups/radar-2026-09-17.zip data/recovery-check.db
```

La restauration ne remplace pas une base existante et n'active pas la base
récupérée. L'audit de conservation ne remplace pas ce test de récupération.
