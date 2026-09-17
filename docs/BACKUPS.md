# Sauvegardes SQLite et récupération

Les commandes `backup create/verify/restore/plan` fonctionnent hors réseau. Les sauvegardes conservent toutes les tables : offres, sources, versions, scores, candidatures et leurs modifications, file d'alertes et historique des décisions. Aucun changement de schéma ni sélection automatique d'une nouvelle base.

## Créer et vérifier une sauvegarde

Depuis la racine du projet, avec l'environnement Python activé :

```powershell
trading-radar backup create data/backups/radar-2026-09-17.zip
trading-radar backup verify data/backups/radar-2026-09-17.zip
```

Sur ce poste, on peut remplacer `trading-radar` par `.\.venv\Scripts\python.exe -m trading_radar`. Choisir un nom nouveau à chaque sauvegarde : une destination existante est refusée, même si elle est vide. `create` suit `DATABASE_URL` et la configuration habituelle ; `--config-dir` choisit le répertoire de configuration, `--demo` choisit `data/demo.db`. Une base absente ou en mémoire est refusée. `verify` fonctionne sans configuration.

Le snapshot utilise l'API de sauvegarde SQLite : il inclut les transactions validées encore dans le journal WAL et exclut les écritures non validées. Copier uniquement `jobs.db` pendant un scan pourrait perdre ces transactions. La sauvegarde peut coexister avec un scanner : elle représente un état transactionnel cohérent, éventuellement entre deux sources d'un scan. Elle n'attend pas la fin d'un cycle complet. La copie est interrompue au prochain contrôle de progression si elle dépasse 30 secondes ; réessayer lorsque l'activité baisse.

L'archive ZIP non compressée contient exactement :

- `database.sqlite3`, autonome, en mode journal DELETE ; les fichiers WAL/SHM ne sont pas nécessaires à sa restauration.
- `manifest.json`, format 1 : date UTC de création après la copie, version du schéma, taille, SHA-256 du fichier SQLite et nombre de lignes de chaque table.

Avant publication, l'archive est relue et vérifiée : membres attendus, taille, empreinte, `integrity_check`, `foreign_key_check`, schéma et comptes de lignes. Une archive tronquée ou incohérente est refusée. Cette version accepte uniquement le **schéma 4 exact** ; une ancienne base doit être migrée séparément avec une version compatible, jamais implicitement pendant la vérification. Des tables, index ou triggers personnalisés entraînent un refus.

## Tester la restauration

```powershell
trading-radar backup restore data/backups/radar-2026-09-17.zip data/restore-check/jobs.db
```

La commande revérifie l'archive et publie une nouvelle base uniquement après succès. Elle refuse la base configurée, ses fichiers associés, toute destination existante et les chemins ayant déjà des fichiers `-wal`, `-shm` ou `-journal`. Elle prend le verrou de la destination ; elle protège également la base et l'archive contre un alias utilisé comme fichier de verrou. Les données ne sont pas fusionnées.

La publication utilise un lien physique créé sans écrasement, depuis un fichier temporaire situé sur le même volume. Le système de fichiers doit prendre en charge les liens physiques (NTFS sur ce poste). S'il ne les prend pas en charge, la commande échoue sans utiliser une copie partielle à la place. Les permissions Unix du fichier publié sont limitées au propriétaire ; sur Windows, les droits du dossier s'appliquent.

L'exercice du lot 19 a créé `data/backups/radar-lot19-2026-09-17.zip` et `data/restore-check/lot19/jobs.db`. Les nombres de lignes et empreintes du contenu des **11 tables** ont été comparés à la base en service : égalité complète, **811 offres**, **809 actives**. Voir [le bilan](VALIDATION-LOT19.md).

## Reprendre le service après une perte

1. Arrêter le watcher et les autres processus qui écrivent dans la base.
2. Vérifier l'archive choisie et la restaurer vers un **nouveau chemin** avec la commande ci-dessus. Garder la base endommagée pour diagnostic.
3. Configurer explicitement `DATABASE_URL` vers ce nouveau fichier, avec `ALERTS_ENABLED=false` et `deadline_reminders_enabled: false`. Vérifier les éventuelles variables d'environnement qui priment sur les fichiers de configuration.
4. Lancer `doctor`, `stats`, `applications list` et `alerts list --all` sur cette configuration. Le premier accès normal avec `Repository` réactive WAL. Comparer les totaux et le suivi à ce qui est attendu à la date de sauvegarde.
5. Revoir les alertes et l'âge des données avant de réactiver l'exploitation et, si souhaité, les notifications. Effectuer une actualisation avec les alertes désactivées si les offres sont anciennes.

Les changements postérieurs au snapshot sont perdus lors d'un retour à celui-ci. Les états d'alertes sont conservés **exactement** : un pending sauvegardé peut avoir été livré depuis, et une offre apparue après la sauvegarde peut être redécouverte. La restauration seule ne peut pas déterminer les messages déjà reçus. Garder les envois désactivés pendant ce contrôle ; utiliser les [décisions explicites](ALERTS.md) pour les alertes à abandonner ou à résoudre. Les commandes de sauvegarde n'initialisent jamais Telegram, même si les alertes sont activées dans la configuration.

## Conservation et périmètre

`trading-radar backup plan data/backups --json` vérifie les archives ZIP du dossier
et propose une conservation combinant sauvegardes récentes, quotidiennes et
hebdomadaires. La commande ne supprime aucun fichier. Une archive invalide bloque
les recommandations de retrait ; les limites, dates UTC et motifs sont décrits
dans [BACKUP-RETENTION.md](BACKUP-RETENTION.md).

Les archives ne contiennent ni `.env`, ni les fichiers YAML, ni les CSV, logs ou code. Conserver la configuration et une version compatible du programme séparément, avec les secrets dans un emplacement adapté. Les notes de candidature et autres données personnelles présentes en base sont dans l'archive.

Les [archives de santé](MONITORING.md), ajoutées au lot 21 sous `data/health-history`, sont également séparées du snapshot SQLite. Copier ce dossier à part pour conserver l'historique de supervision.

Le SHA-256 détecte une altération par rapport au manifeste ; il ne constitue pas une signature. Le ZIP n'est pas chiffré. Conserver une copie vérifiée sur un stockage distinct et protégé : la sauvegarde locale du lot 19 ne protège pas contre une perte du disque. Aucune planification, suppression automatique, copie distante ou politique de rétention n'est activée par ces commandes. Le build Docker et la reprise sur VPS restent à valider.
