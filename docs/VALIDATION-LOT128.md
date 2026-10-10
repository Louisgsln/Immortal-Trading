# Lot 128 — réduire les lectures du journal d’erreurs

L’extension des employeurs a révélé un coût de contrôle de santé du Dashboard :
une recherche sans date de dernier échec parcourait tout le journal, même pour
les sources qui n’avaient jamais échoué. Les échecs déjà suivis d’un succès étaient
également relus alors que leur cause n’était plus affichée.

Le contrôle lit maintenant les causes des seuls échecs actuels. Les contrôles
SQLite, conflits, lacunes, fraîcheur et timestamps restent exécutés. Les premiers
échecs et les restrictions d’accès gardent leur diagnostic.

Validation : 274 tests ciblés passent après les 5 092 tests de la livraison
125–127 ; Ruff, format et mypy passent. Trois tests vérifient l’absence de lecture
historique inutile et le maintien du diagnostic d’un premier échec.
Sur la même limite de 0,5 CPU, le contrôle est passé d’environ 32 à 14 secondes
pendant les mesures. L’image a passé le contrat du Dashboard avant activation.
La limite du Dashboard est portée de 0,5 à 1 CPU sur le VPS à deux cœurs, pour
raccourcir les ouvertures pendant la collecte. Mémoire, isolation et permissions
restent conservées.

L'image `immortal-trading:lot128-health-performance-final-20261010` est installée
sur radar, Telegram, sauvegardes et Dashboard. Les cinq conteneurs tournent avec
leur politique de redémarrage ; les quatre unités systemd sont actives et activées.
Le contrôle HTTPS final mesure **7,748 secondes** pour le Dashboard de 1 320 fiches.
Cette ouverture observée est distincte du benchmark isolé de contrôle de santé.

Le contrat effectif valide 86 contrôles, sept modules et les empreintes des assets.
La [CI 38035281431](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38035281431)
a réussi ses six jobs : Python 3.11 à 3.14, JavaScript et construction Docker
avec contrôle des assets et restauration isolée.
Le même lien privé ouvre le suivi modifiable ; Dashboard sans identifiant ni mot
de passe, cookie protégé, CSRF et contrôles d'origine conservés. Le Dashboard ne
contient pas les identifiants Telegram et n'envoie pas d'alertes.

Sauvegarde vérifiée, 1 320 identifiants et candidatures conservés, 48 alertes et
96 lignes d'historique inchangées, curseur et préférences Telegram conservés.
Les incidents de sources restent signalés : BNP ancien, Optiver partiel et trois
échecs récents Workday. Une restriction employeur ne désactive pas le watcher.
Les références stages sont validées pour 61/63 sources ; les 38 ajouts ont tous
réussi leur collecte. Preuve : [DELIVERY-LOT128.json](DELIVERY-LOT128.json).

Le profilage laisse une priorité d'architecture : mesurer puis regrouper les
lectures de conflits et lacunes par source, sans supprimer ces contrôles.
