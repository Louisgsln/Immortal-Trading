# Installation Docker sur le poste Windows

État mis à jour le **23 septembre 2026**, après installation de WSL par l’utilisateur.

## Validation locale réussie — 23 septembre

- WSL **2.7.14.0**, noyau **6.18.33.2-2**, version par défaut 2.
- Docker Desktop **4.91.0** démarré ; distribution `docker-desktop` en cours
  d’exécution sous WSL 2, contexte `desktop-linux`, moteur **29.8.0**, Linux amd64.
- Configuration Compose valide et image `trading-radar-local:lot41` construite
  depuis le code du lot 41. Identifiant du manifeste local :
  `sha256:ad7a1f41001d9aeb7e3ecf875a03bcfc45e467b5b41f27a648d2841d5b2cd06e`.
- ENTRYPOINT vérifié ; scénario `scripts/smoke_container.py` réussi dans un
  volume neuf, UID/GID **10001**, réseau coupé, racine en lecture seule,
  capacités retirées et `no-new-privileges`.
- Huit offres synthétiques, déduplication, aperçus, exports, historique,
  conservation et sauvegarde/restauration vérifiés : **onze tables identiques**.
- Preuves copiées vers `data/discovery/windows-docker-20260923/`. Conteneur et
  volume de test supprimés après contrôle de leur identité et de leur étiquette ;
  image conservée pour la suite.
- Onze tables de la base réelle et CSV inchangés. Aucun watcher, collecte réelle,
  envoi de notification ni redémarrage Windows lancé par cet exercice.

Le blocage initial WSL est levé. Restent la mise en exploitation régulière,
la surveillance prolongée et une copie distante vérifiée des sauvegardes.

## Historique de l’installation — 17 septembre

## Effectué

- Docker Desktop **4.91.0** installé pour FlowUP dans `%LOCALAPPDATA%\Programs\DockerDesktop`.
- Docker CLI **29.8.0** et Compose **5.5.1** exécutés avec succès.
- Téléchargement officiel Docker ; signature Authenticode Docker Inc. valide et SHA-256
  conforme au manifeste winget : `ac405b09942701770d581b173747fc1024cf0e6047cbe60f13d1df85437311ac`.
- Installation `--user --quiet --accept-license --backend=wsl-2`, code de sortie zéro.
- `.env` créé depuis l’exemple, avec alertes désactivées et identifiants Telegram vides.
  Aucun fichier existant remplacé. `docker compose config --quiet` réussit.
- Service Windows LanmanServer actif et automatique ; hyperviseur Windows détecté.
- Onze tables de la base et CSV du projet inchangés.

### Blocage initial, résolu le 23 septembre

WSL n’était pas installé. L’installation winget de Microsoft.WSL avait échoué avec
`0x80073d28` : privilèges administrateur requis. Le lancement élevé de
`wsl --install --no-distribution` a demandé une confirmation Windows ; l’utilisateur
étant absent, la demande a expiré/été annulée sans exécution du script élevé.
Le moteur Docker local n’est pas démarré. Le build et l’exercice conteneur ont
depuis réussi sur GitHub Actions au [lot 36](VALIDATION-LOT36.md) ; leur vérification
sur ce poste Windows reste à faire.

### Procédure préparée pour terminer l’installation

1. Ouvrir **PowerShell en tant qu’administrateur**, puis accepter la confirmation Windows.
2. Exécuter :

   ```powershell
   wsl --install --no-distribution
   ```

3. Redémarrer Windows si l’installation le demande, après avoir enregistré son travail.
4. Ouvrir Docker Desktop et attendre le démarrage du moteur Linux.
5. Dans un nouveau terminal, vérifier `wsl --version`, `docker version` et
   `docker compose version`. Docker doit afficher un serveur, pas seulement le client.
6. Reprendre avec Codex sur ce poste le build et le scénario synthétique de
   [validation conteneur](OPERATIONS.md#vérifier-avant-de-démarrer-le-watcher).

Le scénario utilisera un volume neuf, des données synthétiques et un réseau coupé.
Ne pas lancer `docker compose up` pour cet exercice : cette commande démarre le watcher.
Aucun redémarrage Windows ni watcher n’a été lancé pendant cette installation.

## Preuves locales

`data/discovery/docker-setup/` conserve l’installateur, les journaux d’installation,
le script WSL préparé et `status.json`. Le script WSL ne redémarre pas Windows.
Les commandes Docker peuvent nécessiter un nouveau terminal pour prendre en compte
le PATH ajouté par l’installateur.

Références officielles : [installation Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/),
[commandes WSL](https://learn.microsoft.com/en-us/windows/wsl/basic-commands).
