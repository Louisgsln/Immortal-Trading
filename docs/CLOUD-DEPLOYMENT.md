# Scanner sur un hôte Linux

Déploiement du lot 103, validé sur Linux amd64 et dans la
[CI publiée](https://github.com/Louisgsln/Immortal-Trading/actions/runs/37417323727).
La cible choisie est [OVH VPS-1](OVH-SETUP.md) ; ces étapes de migration
s'appliquent aussi à une autre VM Ubuntu adaptée.

## Préparer l'accès

Créer le compte et la VM depuis la console de l'hébergeur. Utiliser une clé
SSH locale pour l'accès durable et conserver sa partie privée hors du dépôt
et du chat. N'ouvrir que SSH pour
l'administration, depuis l'adresse de l'opérateur lorsque possible. Le scanner
utilise les connexions sortantes HTTPS aux sites employeur et à Telegram.
Aucun port web n'est publié par `compose.cloud.yaml`.

La session cloud Codex actuelle ne dispose ni d'identité d'hébergeur ni d'accès
TCP à une VM. L'accès à l'hôte exige une session Codex attachée à ce serveur ou
la configuration réseau/SSH prise en charge par l'environnement. Modifier un
fichier local de politique réseau ne débloque pas ces accès.

Sur la VM, utiliser le cloud-init proposé ou installer Docker Engine, son
plugin Compose, Buildx et Git. Docker doit démarrer avec le système. Le répertoire
persistant doit exister et être accessible à l'UID/GID 10001 :

```bash
sudo install -d -o 10001 -g 10001 -m 0700 /srv/immortal-trading/data
git clone https://github.com/Louisgsln/Immortal-Trading.git
cd Immortal-Trading
# Lot 103 validé : choisir explicitement un nouveau commit pour une autre livraison.
git checkout --detach 3afcdbf7b9e1f2ba5e951238d3317d5685fddbf3
cp .env.cloud.example .env.cloud
chmod 600 .env.cloud
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml config --quiet
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml build radar
```

Compléter `.env.cloud` directement sur le serveur, avec le secret Telegram déjà
utilisé et sa destination privée. Garder `ALERTS_ENABLED=false`, le contrôle
Telegram désactivé et `RADAR_CUTOVER_CONFIRMED=false` pendant la migration.
Conserver les YAML de configuration réellement utilisés sur Windows si leurs
paramètres diffèrent du dépôt. Les fichiers du dossier `config` monté doivent
être lisibles par l'UID 10001 ; conserver les secrets dans `.env.cloud`.
Le tag d'image identifie une livraison ; aucune
mise à jour automatique depuis une branche mouvante n'est effectuée.

## Migrer les données sans second scanner

1. Sur Windows, arrêter **watch et telegram** et confirmer la fin des processus.
   Suspendre aussi les modifications de candidatures pendant le transfert final.
2. Créer et vérifier une sauvegarde cohérente avec `backup create` et
   `backup verify`, selon [BACKUPS.md](BACKUPS.md). Conserver le paquet et la
   base Windows pour un retour arrière. Les archives contiennent des données
   personnelles : les transférer par SSH/SFTP vers ce serveur choisi.
3. Placer la sauvegarde dans le sous-dossier `backups` du répertoire persistant,
   avec des droits permettant sa lecture par l'UID 10001. Conserver séparément
   `.env`, la configuration, `health-history` et les états Telegram utiles.
   Dans la migration, éviter de redémarrer deux écouteurs du même bot.
4. Restaurer vers une **nouvelle base absente**. L'override de `DATABASE_URL`
   protège un chemin de référence distinct pendant cette seule commande ; il
   ne crée pas ce chemin. Une base `jobs.db` déjà présente est refusée :

```bash
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml run --rm \
  -e DATABASE_URL=sqlite:////app/data/restore-reference.db \
  --entrypoint trading-radar radar backup restore \
  data/backups/windows-cutover.zip data/jobs.db
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml run --rm radar preflight
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml run --rm \
  --entrypoint trading-radar radar stats
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml run --rm \
  --entrypoint trading-radar radar alerts list --all
```

Comparer les totaux, candidatures et historiques à la sauvegarde. Les états
d'alerte restaurés peuvent être antérieurs à des messages déjà livrés ; revoir
les pending/unknown avant de réactiver les envois. Aucun recalcul des scores ni
réenvoi historique n'est déclenché par ces contrôles.

Après confirmation de l'arrêt des anciens services, mettre
`RADAR_CUTOVER_CONFIRMED=true`. Le collecteur refusera de démarrer tant que cette
valeur exacte n'est pas présente ou si la base est absente/incompatible :

```bash
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml up -d radar backups
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml ps
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml logs --tail 100 radar backups
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml exec radar trading-radar health
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml exec radar trading-radar runtime
```

Le premier cycle doit produire des événements de succès réels et un heartbeat
récent. Le healthcheck contrôle les deux ; les domaines bloqués ou un catalogue
refusé restent visibles, même lorsque le processus tourne. Le statut unhealthy
ne redémarre pas automatiquement un processus encore vivant ; les sorties de
processus sont reprises par `restart: unless-stopped`.

Après revue de la file d'alertes, activer les alertes souhaitées dans `.env.cloud`
et recréer `radar` avec `up -d radar`. Pour retrouver `/status` et la surveillance
privée, activer `TELEGRAM_CONTROL_ENABLED=true`, puis :

```bash
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml --profile telegram up -d telegram
```

Les instances sont séparées mais partagent les mêmes données. Les verrous
existants du radar protègent une seule instance locale de chaque rôle ; ils ne
peuvent pas constater l'arrêt d'un ancien PC distant.

## Sauvegardes, maintenance et arrêt

Le service `backups` crée immédiatement une archive cohérente vérifiée, puis
chaque 24 heures. Un échec est journalisé sans texte privé et réessayé après
dix minutes. Son état se trouve dans `jobs.cloud-backups.json`. Une seule boucle
peut utiliser ce chemin grâce à un verrou. Les archives ne sont pas supprimées.
Contrôler l'espace et examiner `backup plan` avant toute rétention ; prévoir une
copie vérifiée sur un autre stockage choisi, par exemple le PC local. Les sauvegardes sur le même
disque ne protègent pas contre la perte de la VM.

Chaque nouvelle version doit suivre : arrêt des services, sauvegarde vérifiée,
construction du commit validé avec un nouveau tag, contrôles puis reprise.
Les données persistent dans le dossier hôte ; aucun volume anonyme nouveau
n'est créé pour remplacer la base. Les logs sont limités à trois fichiers de
10 Mo par service et le conteneur utilise l'UID 10001, une racine en lecture
seule et des capacités retirées.

```bash
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml --profile telegram stop
```

Arrêter le cloud et confirmer ses processus avant de reprendre Windows. Ne pas
reprendre une ancienne base Windows si le suivi a changé dans le cloud : créer
une sauvegarde fraîche, vérifier et restaurer vers un nouveau chemin d'abord.
Le dashboard local actuel reste fermé au réseau public ; sa publication distante
n'est pas incluse dans ce déploiement du scanner.
