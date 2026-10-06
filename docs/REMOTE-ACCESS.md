# Administrer le VPS directement depuis ChatGPT

Objectif choisi le 6 octobre 2026 : ce chat utilise un terminal sur le VPS Ubuntu,
puis administre le scanner et Telegram. Le PC Windows ne sert qu'à lancer la
configuration initiale depuis son accès SSH existant. Il pourra ensuite être éteint.

Le plugin **Remote Desktop Commander** est installé dans le compte du propriétaire.
Cela ne prouve ni l'appairage du VPS ni la disponibilité de ses outils dans le chat.
La chaîne est vérifiée seulement après une commande réelle exécutée depuis ce chat.

## Installation initiale sur Ubuntu

Dans le terminal SSH, sous l'utilisateur `ubuntu`, extraire le helper de la version
publiée puis lancer `python3 scripts/cloud_remote_access.py install`. Lorsque le
helper est extrait dans un répertoire temporaire, définir `RADAR_PROJECT_DIR` au
répertoire du projet. Le helper se copie dans un répertoire privé avant de démarrer
le service ; l'effacement du répertoire temporaire est alors possible.

Le helper installe `nodejs`, `npm` et `ripgrep` depuis Ubuntu, exige Node.js 22 ou
plus récent, puis installe Desktop Commander **0.2.52** dans un préfixe privé. Les
scripts d'installation npm sont désactivés. La version et l'intégrité SHA-512 du
paquet principal doivent correspondre à la publication inspectée. Les dépendances
transitives sont enregistrées dans le lock npm créé sur le VPS ; leur résolution
initiale n'est pas épinglée par le dépôt Python.

Le service système `immortal-trading-remote.service` exécute l'agent en tant que
`ubuntu`, démarre après le réseau et est activé au redémarrage. Les échecs relancent
le service après 30 secondes. Un arrêt demandé au service termine aussi ses enfants.
Une deuxième installation conserve le service déjà actif ; un lanceur concurrent
identifié ou un service étranger du même nom bloque l'installation.

L'installation ajoute cet accès d'administration sans lancer un nouveau scanner,
modifier `.env.cloud`, consulter la base, envoyer de message Telegram ou mettre à
jour l'image applicative. Aucun port d'administration supplémentaire n'est ouvert.

## Appairage obligatoire

Le résultat `ACCES_DISTANT` affiche un `pairing_url` et un `pairing_code` lorsqu'une
validation est nécessaire. Ouvrir ce lien dans son navigateur, se connecter au
compte Desktop Commander utilisé pour le plugin, comparer le code affiché et
valider le VPS. Le code est temporaire ; il ne doit pas être transmis à un tiers.

Si le plugin demande encore une connexion OAuth dans ChatGPT, la terminer avec le
même compte. L'installation du plugin et l'appairage de la machine sont deux étapes
distinctes du [guide officiel](https://github.com/desktop-commander/remote-desktop-commander/blob/main/docs/SETUP.md).

Le programme conserve sa session sur le VPS, dans
`~/.desktop-commander-device/device.json`, avec des permissions privées. Ne pas
copier ce fichier, afficher ses jetons ou les ajouter au dépôt. Le contrôleur
ne lit pas ces jetons ; il contrôle seulement le type, le propriétaire et les
permissions du fichier existant.

Le contrôleur intercepte la sortie de l'agent et écarte les arguments et résultats
des outils avant les journaux systemd. Il publie seulement les instructions initiales
d'appairage et un état borné dans `~/.local/share/immortal-trading-remote/status.json`
(0600). Cet état initial n'est pas une sonde continue de disponibilité du relais.

## Vérifier la chaîne complète

L'état `agent_connected` indique que l'agent a annoncé sa connexion. Le champ
`chat_access_verified` reste `false` dans le helper : seul un appel effectif des
outils du plugin depuis le chat peut vérifier la dernière partie de la chaîne.

Une fois les outils disponibles, sélectionner le VPS appairé, puis consulter
l'identité de l'hôte, le répertoire du projet et `docker compose ps`. Vérifier la
présence d'un seul scanner et d'un seul service Telegram avant toute intervention.
Poursuivre ensuite le diagnostic public des champs en échec, sans restaurer une
ancienne base ni réinitialiser le curseur Telegram.

État local, dans SSH :

```bash
python3 "$HOME/.local/share/immortal-trading-remote/controller.py" status
```

Arrêter et désactiver seulement cet accès distant :

```bash
python3 "$HOME/.local/share/immortal-trading-remote/controller.py" stop
```

Cela conserve les services du scanner et Telegram. Pour invalider aussi
l'autorisation distante, révoquer le VPS dans le tableau de bord du fournisseur.

Cet accès est un terminal avec les permissions du compte `ubuntu`, y compris ses
droits sudo déjà configurés. Le modèle de confiance est documenté par le
[fournisseur](https://github.com/desktop-commander/remote-desktop-commander/blob/main/SECURITY.md).
La chaîne passe par son relais chiffré ; elle ne constitue pas une nouvelle
connexion SSH directe du cloud Codex au VPS. Aucun abonnement supplémentaire
n'est souscrit par cette installation.
