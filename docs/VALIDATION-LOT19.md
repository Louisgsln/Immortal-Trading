# Validation du lot 19 — Sauvegardes et restauration SQLite

17 septembre 2026, Windows / Python 3.14.3. Suite de la [gestion des alertes incertaines](VALIDATION-LOT18.md).

## Fonction livrée

Commandes `backup create/verify/restore`, hors réseau, sans initialisation de Telegram et sans migration implicite. La sauvegarde utilise l'API SQLite pour produire un snapshot transactionnel incluant le WAL validé. L'archive autonome contient la base en mode DELETE et un manifeste : format 1, schéma 4, date UTC, taille, SHA-256 et nombre de lignes de chaque table.

Les contrôles portent sur l'archive effectivement écrite : membres exacts, taille, empreinte, intégrité SQLite, clés étrangères, schéma et comptes de lignes. Ils sont répétés avant toute restauration. Une archive invalide n'est pas publiée comme nouvelle base.

La publication finale utilise un lien physique sans écrasement. La restauration exige un nouveau chemin, prend son verrou et protège la base configurée, les fichiers associés et les alias utilisés comme verrou. Les temporaires sont nettoyés en cas d'échec. La configuration et les états d'alertes ne sont pas modifiés.

Guide : [BACKUPS.md](BACKUPS.md).

## Exercice réel

Les trois commandes CLI ont été exécutées successivement : création, vérification, restauration. La base en service a été protégée par son verrou d'écriture pendant la comparaison des contenus.

| Élément | Résultat |
| --- | --- |
| Archive | `data/backups/radar-lot19-2026-09-17.zip` |
| Base restaurée séparée | `data/restore-check/lot19/jobs.db` |
| Taille de l'archive | 20 914 889 octets |
| Taille SQLite restaurée | 20 914 176 octets |
| Offres conservées / actives | 811 / 809 |
| Candidatures / associations de sources | 811 / 811 |
| Sources enregistrées / scans | 24 / 44 |
| Versions d'offres / historique de scores | 923 / 921 |
| Alertes / historique d'alertes | 0 / 0 |
| Historique de candidature | 0 |
| Version du schéma | 4, aucune migration |

Les nombres de lignes et SHA-256 du contenu ordonné des **11 tables** sont identiques dans les trois états : source avant, source après, copie restaurée. `integrity_check` retourne `ok` et `foreign_key_check` ne trouve aucune violation. Les enregistrements métier de la base en service sont inchangés ; aucun événement synthétique n'y a été ajouté.

Les preuves locales figurent dans `data/discovery/lot19/` : `before.json`, `create.json`, `verify.json`, `restore.json`, `after.json`, `restored.json`, `summary.json`. Les archives, bases de contrôle et preuves sont ignorées par Git.

Alertes et rappels restent désactivés. Aucun watcher lancé, message envoyé ou portail rescanné. Les scénarios d'historique non vide sont validés dans les bases temporaires des tests.

## Vérification automatisée

- **900 tests réussis**, soit **53 supplémentaires** ; couverture globale **95 %**.
- Module de sauvegarde **97 %**, CLI de sauvegarde **95 %**.
- Ruff valide sur **95 fichiers** ; mypy valide sur **41 modules**.
- Récupération exacte de toutes les tables avec WAL encore présent ; écritures non validées exclues ; sauvegarde possible sous le verrou applicatif d'un scanner.
- Notes françaises, candidature Applied, historique utilisateur et alerte unknown avec ses tentatives et décisions préservés. La copie restaurée s'ouvre avec le dépôt SQLite normal de l'application.
- Refus d'une base absente, en mémoire, ancienne ou future ; aucun schéma créé dans la source ni migration pendant ces commandes.
- Schéma incomplet ou inattendu, clé étrangère cassée, fichier SQLite corrompu, empreinte erronée, manifeste incohérent et ZIP tronqué refusés.
- Membres ZIP supplémentaires, chemins sortant de l'archive, noms dupliqués, manifeste trop volumineux et compression hors format refusés.
- Destinations existantes, fichiers WAL/SHM/journal orphelins, verrou occupé et alias vers les données protégées refusés.
- Création concurrente de la destination au moment de la publication : le fichier de l'autre processus est préservé, pour sauvegarde comme restauration.
- Dépassement du délai de copie : aucun fichier final publié. Nettoyage des temporaires vérifié après les échecs.
- Parcours CLI complet sans initialisation de Telegram même avec `ALERTS_ENABLED=true` ; vérification d'une archive sans configuration.

## Limites et suite logique

L'archive contient les données au moment du snapshot ; une restauration ne reconstitue pas les changements ultérieurs. Elle préserve les états d'alertes, mais ne sait pas quels messages ont été livrés depuis. Le guide prévoit une reprise avec notifications désactivées et revue des alertes avant réactivation.

La sauvegarde est locale, non chiffrée et non signée. Le manifeste ne remplace pas une copie sur un stockage distinct et protégé. La configuration, les secrets, le code et les exports ne font pas partie du snapshot. Aucune rétention ou planification automatique n'est activée.

La publication par lien physique a été validée sur ce poste Windows ; les systèmes de fichiers ne prenant pas en charge ces liens sont refusés. Les environnements Linux, Docker et VPS ainsi que la résistance à une coupure matérielle restent à valider.

Prochaine étape : **verrouillage des dépendances, build Docker et exercice de reprise sur le volume du conteneur**, puis tests prolongés et suivi de santé.
