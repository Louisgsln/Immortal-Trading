# Vérification du moteur de conteneurs — lot 27

Vérification locale du 17 septembre 2026, en lecture seule.

## Résultat

Le moteur nécessaire à une validation Docker locale reste indisponible. La présence du lanceur `wsl.exe` ne signifie pas que WSL est installé.

| Contrôle | Résultat |
| --- | --- |
| Recherche de `docker` dans le PATH | Introuvable |
| Recherche de `podman` dans le PATH | Introuvable |
| Recherche de `wsl` dans le PATH | `C:\WINDOWS\system32\wsl.exe` |
| `wsl --status` | Code de sortie 50 ; WSL non installé |
| `wsl --list --quiet` | Code de sortie 1 ; WSL non installé |
| `wsl --list --running --quiet` | Code de sortie 1 ; WSL non installé |

Les trois commandes WSL indiquent que le Sous-système Windows pour Linux n'est pas installé. Aucune distribution disponible n'a donc pu être identifiée pour poursuivre la vérification d'un moteur Linux.

## Portée

Aucune installation, mise à jour, activation de fonctionnalité Windows, exécution de distribution ou construction d'image n'a été effectuée. Les commandes ont été confirmées par leur code de sortie via `subprocess.run` ; aucun test CI distant n'a été lancé.

Ce contrôle ne constitue pas une validation du Dockerfile ni une exécution de la CI. La validation locale en conteneur reste à réaliser sur un environnement disposant d'un moteur opérationnel.
