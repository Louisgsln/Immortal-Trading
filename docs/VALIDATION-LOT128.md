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
restent conservées. Déploiement et réponse HTTPS finale en cours de vérification.
