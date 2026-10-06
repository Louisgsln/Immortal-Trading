# Validation du lot 107

Le scanner et Telegram tournent sur OVH, mais cette session cloud n'a ni accès
TCP SSH accordé, ni identité SSH, ni outil Remote Desktop Commander disponible.
Le plugin est bien installé dans le compte du propriétaire. Sa demande explicite
est de raccorder directement le VPS pour supprimer les transferts via le PC.

## Préparation réalisée

Le code publié de Desktop Commander **0.2.52** et son archive npm ont été inspectés.
L'archive a été vérifiée par SHA-512 contre l'intégrité publiée. L'agent garde sa
session localement par défaut et propose un appairage par validation navigateur ;
il ne nécessite pas de saisir une clé SSH privée ou un jeton Telegram dans le chat.

Le helper `scripts/cloud_remote_access.py` prépare un service système sous
`ubuntu`, une installation npm privée avec scripts d'installation désactivés et
une vérification de version et d'intégrité avant exécution. La relance ne touche
pas un service déjà actif, un lanceur concurrent identifié bloque l'installation
et un service étranger du même nom est préservé.

L'agent affiche par défaut les arguments et résultats des outils. Le contrôleur
écarte cette sortie avant les journaux systemd et ne conserve que les instructions
initiales d'appairage. Les fichiers d'état et identifiants locaux restent privés.
Un service actif et une annonce `agent_connected` ne prouvent pas l'accès depuis
ce chat ; le helper conserve explicitement `chat_access_verified=false`.

## Vérifications locales

Les **21 tests** du helper passent. Ils vérifient l'installation ciblée et ses
blocages, la répétition sans relance, la conservation des services applicatifs, la vérification npm, la
confidentialité des sorties et l'arrêt d'un vrai processus enfant synthétique.
La syntaxe du service est contrôlée avec `systemd-analyze verify` sans l'enregistrer.
Les tests ne démarrent pas l'agent réel et n'effectuent aucun appairage réseau.

L'installation npm avec les scripts désactivés a aussi été exécutée dans un
préfixe temporaire local : 539 paquets installés et intégrité du paquet principal
conforme. La commande réelle `remote --help` de cette installation s'exécute avec
Node.js 24.19.0. Pour cette vérification locale uniquement, `os.homedir()` est
redirigé par un préchargement Node vers un domicile synthétique privé, car le
domicile annoncé par le cloud ne permet pas de créer les fichiers du plugin.
Les variables système `HOME` ne sont pas modifiées et cette adaptation ne figure
pas dans le service Ubuntu. Cette vérification confirme le chargement de la CLI,
pas son accès au relais ni le fonctionnement de tous ses outils.

Les **73 tests** ciblés de l'accès distant, des helpers d'activation/préactivation
Telegram et du diagnostic des sources passent. Ruff, format (289 fichiers),
mypy (101 fichiers source) et contrôle du diff passent également.

## Vérifications distantes restantes

L'installation sur Ubuntu 26.04, l'appairage du VPS et la connexion effective du
plugin depuis ce chat ne sont pas encore réalisés. Ils nécessitent d'abord le
bloc d'installation depuis l'accès SSH existant et la validation du code par le
propriétaire. Ce lot n'active aucun nouvel envoi Telegram, ne réinitialise aucun
état et ne remplace pas l'image du scanner.
