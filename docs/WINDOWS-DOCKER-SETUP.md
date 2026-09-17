# Installation Docker sur le poste Windows

État au **17 septembre 2026**, après autorisation explicite de l’utilisateur.

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

## Étape bloquante

WSL n’est pas installé. L’installation winget de Microsoft.WSL a échoué avec
`0x80073d28` : privilèges administrateur requis. Le lancement élevé de
`wsl --install --no-distribution` a demandé une confirmation Windows ; l’utilisateur
étant absent, la demande a expiré/été annulée sans exécution du script élevé.
Le moteur Docker n’est pas démarré ; le build et l’exercice conteneur restent à faire.

## Reprendre au retour sur le poste

1. Ouvrir **PowerShell en tant qu’administrateur**, puis accepter la confirmation Windows.
2. Exécuter :

   ```powershell
   wsl --install --no-distribution
   ```

3. Redémarrer Windows si l’installation le demande, après avoir enregistré son travail.
4. Ouvrir Docker Desktop et attendre le démarrage du moteur Linux.
5. Dans un nouveau terminal, vérifier `wsl --version`, `docker version` et
   `docker compose version`. Docker doit afficher un serveur, pas seulement le client.
6. Reprendre avec Codex le build et le scénario synthétique de
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
