# Installer le scanner sur OVH

Cible choisie le **6 octobre 2026** : OVH VPS-1 sous Ubuntu 26.04 LTS.
Le propriétaire n'a pas encore de compte ni de VPS. Le scanner distant reste
à installer ; le lot 103 et son
parcours Docker sont déjà [validés par la CI](https://github.com/Louisgsln/Immortal-Trading/actions/runs/37417323727).

## 1. Créer le compte et choisir le VPS

Ouvrir [les VPS OVHcloud](https://www.ovhcloud.com/fr/vps/), choisir VPS-1,
puis créer son compte dans le parcours de commande. L'identité, les coordonnées
de paiement et la validation de la commande se renseignent directement chez OVH.

| Réglage | Choix pour démarrer |
|---|---|
| Offre | VPS-1 : 2 vCores, 4 Go de RAM, 40 Go SSD NVMe |
| Système | Ubuntu 26.04 LTS, installation Linux simple |
| Localisation | France, centre de données standard disponible |
| Facturation | Mensuelle, sans engagement annuel pour le premier essai |
| Options | Conserver les inclusions ; aucun supplément payant nécessaire au scanner |

La page française affiche **à partir de 3,81 € HT / 4,57 € TTC par mois**.
Son lien « Configurer » présélectionne `pricing=upfront12` : ce chiffre n'est
pas un prix mensuel sans engagement confirmé. Vérifier dans le panier le total
TTC dû aujourd'hui, la durée d'engagement, la périodicité et le tarif de
renouvellement avant paiement. Le prix exact du panier n'est pas vérifiable
dans cette session. Ce choix OVH est payant, contrairement au budget initial.

Ubuntu 26.04 LTS figure parmi les [OS inclus chez OVH](https://www.ovhcloud.com/fr/vps/os/).
[Docker prend en charge cette version](https://docs.docker.com/engine/install/ubuntu/).
Les paquets Ubuntu `docker.io`, `docker-buildx` et `docker-compose-v2` existent
dans [Resolute 26.04](https://packages.ubuntu.com/resolute/docker.io).
Le scanner conserve son environnement Python dans l'image Docker validée.
L'installation et les collectes sur ce VPS restent à vérifier après sa création.

Les ressources constituent un point de départ pour le scanner Python et SQLite ;
leur utilisation sera mesurée après installation. Aucun domaine, panneau
cPanel/Plesk ou base managée n'est nécessaire. Garder la sauvegarde quotidienne
incluse : les archives SQLite de l'application et une copie sur le PC la complètent.

## 2. Se connecter après livraison

L'e-mail de livraison indique l'IPv4 et l'utilisateur, normalement `ubuntu`
pour Ubuntu. Selon l'accès choisi, utiliser sa clé SSH locale ou le lien sécurisé
OVH pour obtenir le mot de passe temporaire. Ne transmettre au chat ni mot de
passe, ni clé privée, ni jeton Telegram.

Depuis PowerShell sur le PC, remplacer `IP_DU_VPS` par l'adresse reçue :

```powershell
ssh ubuntu@IP_DU_VPS
```

Si OVH demande de changer le mot de passe temporaire, le faire ; la session
peut se fermer après ce changement. Se reconnecter ensuite avec la même commande.
L'utilisateur indiqué dans l'e-mail prévaut s'il diffère de `ubuntu`.
Pour l'accès durable par clé, suivre le
[guide officiel SSH](https://docs.ovhcloud.com/en/guides/bare-metal-cloud/dedicated-servers/creating-ssh-keys).
Tester cette connexion avant de modifier les méthodes d'authentification.

L'IP et le nom d'utilisateur suffisent à identifier le serveur, mais ne donnent
pas à cette session Codex un accès SSH. La suite peut être exécutée depuis le PC
connecté au VPS, ou dans une session Codex disposant d'un accès réseau et d'une
authentification à cet hôte. La session cloud actuelle n'a pas cet accès.

## 3. Préparer Ubuntu

Sur un VPS Ubuntu 26.04 LTS neuf, dans la session SSH :

```bash
cat /etc/os-release
sudo apt-get update
sudo apt-get install -y git docker.io docker-buildx docker-compose-v2
sudo systemctl enable --now docker
sudo docker compose version
sudo docker buildx version
sudo install -d -o 10001 -g 10001 -m 0700 /srv/immortal-trading/data
```

Buildx est installé explicitement pour construire le Dockerfile avec BuildKit.
Ces commandes installent les outils et préparent le stockage. Elles ne lancent
pas le scanner. Le fichier `deploy/cloud-init.yaml` est une autre méthode
d'initialisation pour les fournisseurs acceptant ces données ; son injection
dans l'interface VPS OVH n'est pas présumée disponible.

## 4. Installer la version validée et migrer

Suivre le [guide commun](CLOUD-DEPLOYMENT.md#préparer-laccès) à partir de
`git clone`. Il épingle le commit validé du lot 103, construit l'image, puis
décrit le transfert de l'état Windows et le démarrage des services.

Le scanner Windows peut rester actif pendant la commande et la préparation du
VPS. L'arrêter, ainsi que son écouteur Telegram et les autres écrivains de la
base, au moment du transfert final. La base restaurée doit conserver les offres,
candidatures et historiques ; revoir les alertes en attente avant de réactiver
les envois. Le démarrage reste bloqué tant que `RADAR_CUTOVER_CONFIRMED=false`.

Après la bascule, vérifier une collecte réussie sur les sources réelles, la
santé du scanner, une sauvegarde vérifiée et la bonne destination Telegram.
Compose prévoit la reprise des services après redémarrage de Docker ; aucun
port web n'est publié. Garder SSH pour l'administration et maintenir Ubuntu
avec ses mises à jour de sécurité.

Références consultées le 6 octobre 2026 : [offre VPS](https://www.ovhcloud.com/fr/vps/),
[première connexion](https://docs.ovhcloud.com/en/guides/bare-metal-cloud/virtual-private-servers/starting-with-a-vps),
[sécurisation du VPS](https://docs.ovhcloud.com/en/guides/bare-metal-cloud/virtual-private-servers/secure-your-vps).
