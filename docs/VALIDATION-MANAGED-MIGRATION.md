# Validation locale des lots 183–184

Préparation d’une migration vers un hébergement géré ; aucun hébergement cible
n’a été provisionné et aucune bascule de production n’est déclarée.

| Contrôle | Résultat local |
|---|---|
| Restauration, sauvegardes, protections Telegram et passerelle privée | 158 tests Python ciblés réussis |
| Interface et suivi des candidatures | 53 tests JavaScript réussis |
| Qualité Python | Ruff, formatage et Mypy réussis |
| Image dédiée | Construite avec images épinglées et `uv.lock`, sans dépendances de développement |
| Docker isolé | Réseau externe désactivé, racine en lecture seule, utilisateur 10001, aucune capacité, `no-new-privileges` |
| Attente | Santé explicite `standby`, aucune base créée, aucun radar ni écouteur Telegram |
| Doublon local | Deuxième service refusé sur le même disque |
| Activation incorrecte | Absence de restauration, mauvais reçu ou mauvaise identité Telegram refusés avant transport |
| Redémarrage | Marqueur synthétique retrouvé sur le même volume, arrêt propre |
| Passerelle réelle | Page privée compatible avec le bridge Sites ; cookie sécurisé, contrôles origine/session/CSRF, racine publique 404 |
| Bundle | Toutes les tables et leurs historiques identiques ; souhaits et historique identiques ; octets du curseur et du heartbeat conservés ; configuration et archives de santé conservées |
| Refus de récupération | Archive altérée, membre manquant, chemin dangereux, fichier symbolique et écrasement refusés |

La capacité privilégiée héritée du binaire Caddy est retirée à la construction :
le port interne est supérieur à 1024, et cette capacité empêcherait son exécution
avec les restrictions de sécurité choisies.

La CI inclut désormais une construction et un smoke test de l’image dédiée, en
plus des vérifications existantes. Son résultat hébergé doit être consulté sur
le commit exact avant de promouvoir cette livraison.

Restent à valider **sur la destination réelle** : compte et coût, schéma/devis du
Blueprint, permissions et capacité du disque, transfert privé, secrets, fraîcheur
et accès des portails depuis la nouvelle adresse réseau, instance unique entre
hôtes, écritures mobiles et Telegram, snapshots et restauration indépendante.
La sauvegarde quotidienne DB locale ne remplace pas une copie externe complète.

[Procédure et retour arrière](MANAGED-MIGRATION.md) · [Carnet](TASK-BOARD.md).
