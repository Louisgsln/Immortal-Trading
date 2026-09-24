# Lot 46 — Récapitulatif Telegram quotidien

Livré et installé le **24 septembre 2026**, commit applicatif `ac1fdb5`.

## Fonctionnalités

- `/digest` affiche le réglage et un aperçu des découvertes pertinentes des
  dernières 24 heures, avec le nombre de sources à jour.
- `/digest_on HH:MM` active et règle l'horaire en Europe/Paris ; sans argument,
  l'horaire mémorisé est réutilisé. `/digest_off` désactive cet envoi uniquement.
- Démarrage au prochain créneau futur, gestion été/hiver, rattrapage limité à
  quatre heures, sans empilement des jours manqués. Une absence de nouvelle
  offre produit un message explicite.
- Date de tentative persistée avant livraison, sans renvoi automatique après
  échec ou incertitude. Le redémarrage et le changement d'horaire ne permettent
  pas un second envoi automatique pour une date de créneau déjà tentée.
- Préférences dans le fichier d'état du bot ; lecture des anciens états avec
  récapitulatif désactivé par défaut et curseur conservé. Les commandes restent
  limitées au propriétaire privé déjà configuré.

Aucun changement de score, de suivi de candidature ni de schéma SQLite.
Les critères de `/new` sont réutilisés. Le service Telegram existant vérifie
l'horaire même en l'absence de messages entrants ; aucune cinquième tâche
Windows n'est nécessaire. `tzdata` devient une dépendance principale verrouillée.

## Validation locale

- Paquet Windows non éditable : **2 803 tests réussis**, couverture **96 %**.
- [CI du commit ac1fdb5](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35999243561) :
  **2 803 tests par version Python 3.11 à 3.14**, couverture 96 %,
  Ruff et mypy réussis. Build Docker et reprise réussis sous UID 10001,
  onze tables synthétiques restaurées identiques.
- Ruff : 192 fichiers ; mypy : 70 modules applicatifs.
- 42 nouveaux cas : activation/désactivation privée, arguments invalides,
  anciens fichiers d'état, aperçu sans effet sur les tables métier, limites
  UTF-16 et liens complets, indisponibilité de la base.
- Horaires été/hiver, heure inexistante du printemps, heure répétée d'automne,
  activation avant/à/après l'heure, rattrapage après minuit et limite de quatre
  heures vérifiés avec des horloges simulées.
- Persistance, reprise après redémarrage, livraison incertaine, échec disque,
  recul de l'horloge et changement d'horaire testés sans envoi réel.

## Déploiement observé

Sauvegarde SQLite vérifiée et copie de l'ancien état Telegram avant activation.
Arrêt effectif des trois services, installation depuis le verrou avec `tzdata`,
activation locale à **09:00 Paris**, puis redémarrage.

À **12 h 29 UTC** : les tâches collecteur, dashboard et Telegram sont en cours
d'exécution ; la tâche de sauvegarde est prête. Dashboard HTTP 200, signal du
collecteur récent, menu privé Telegram avec les sept commandes attendues.
Le paquet installé génère un aperçu de 1 950 unités UTF-16.

Le premier créneau persisté est le **25 septembre 2026 à 07:00 UTC**, soit
**09:00 à Paris**. Aucun envoi automatique de récapitulatif n'est encore
revendiqué : le créneau n'est pas atteint. La commande `/new` précédente a bien
été traitée par le bot à 12 h 19 UTC. L'aperçu de validation est conservé
localement sans message de test ajouté au chat.

Preuves privées ignorées par Git dans `data/windows-service/` :
`lot46-tests.txt`, `lot46-tests.xml`, `lot46-backup.json`,
`before-lot46-telegram-*.json`, `lot46-schedule.json`, `lot46-smoke.json` et
`lot46-preview.txt`. Aucun token ni identifiant de chat publié.
Les cinq journaux GitHub sont conservés dans les `ci-lot46-*.json` locaux.

## Limites

Le PC et le service doivent être en fonctionnement et connectés. L'envoi a lieu
au contrôle suivant l'heure, sans garantie à la seconde. Une tentative échouée
ou incertaine n'est pas retentée automatiquement ce jour-là ; `/digest` reste
disponible pour une nouvelle demande. Une indisponibilité dépassant quatre
heures laisse passer le créneau. Le résumé couvre les 24 heures précédant son
exécution, pas un historique de tous les jours manqués.

Voir le [guide Telegram](TELEGRAM-CONTROL.md). Les rappels de deadline,
la surveillance depuis un système externe et la sauvegarde distante restent
des sujets séparés.
