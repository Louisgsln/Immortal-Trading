# Telegram : état du radar et incidents

Disponible sur ce poste depuis le 24 septembre 2026.

## Utilisation

Dans le chat privé avec `@ImmortalTradingBot` :

- `/status` affiche l'activité du collecteur, le dernier cycle terminé, la santé
  des sources et le nombre d'alertes envoyées ou à vérifier.
- `/help` affiche l'aide ; `/start` affiche également cette aide.

Les dates du rapport sont explicitement en UTC. « Activité récente confirmée »
signifie qu'un signal du collecteur a moins de 90 secondes ; cela ne garantit
pas la réussite de chaque source. Un cycle dépassant 30 minutes est signalé.
Ces commandes consultent la base sans modifier les offres ou les candidatures.

Les alertes d'offres ont des libellés français, les dates connues, le minimum
d'expérience reconnu et la décomposition du score. Un minimum inconnu reste
distinct de zéro. Le score indique une priorité de candidature, pas une
probabilité d'embauche. L'extrait employeur reste dans sa langue d'origine :
aucun résumé IA ni traduction automatique n'est ajouté.

## Notifications d'incident

Le service vérifie périodiquement l'état local et la santé des sources. Un
ensemble de problèmes doit rester stable au moins deux minutes avant envoi.
Deux avis sont espacés d'au moins 30 minutes, y compris le retour à la normale.
Un état identique ne provoque pas de rappel répété. Ces délais sont des minima :
le contrôle est effectué à intervalles d'au moins une minute.

Le service Telegram est indépendant du collecteur et peut signaler son arrêt.
**Il ne peut pas prévenir si le PC entier est éteint ou privé d'Internet.**
Une surveillance depuis un autre système reste à installer pour ce cas.

## Configuration et exploitation

Les deux options sont désactivées par défaut et activées dans le `.env` local :

```dotenv
TELEGRAM_CONTROL_ENABLED=true
TELEGRAM_INCIDENT_NOTICES_ENABLED=true
```

Le token et la destination privée restent dans `.env`, hors Git. Une destination
privée numérique est requise. Seuls les messages récents de cette même personne,
dans son chat privé configuré, sont traités. Groupes, autres expéditeurs et
anciens messages sont ignorés. Le menu est limité à ce chat.

La tâche `Immortal-Trading-telegram` exécute `trading-radar telegram`.
Son journal est `data/windows-service/telegram.log`. Le collecteur actualise
`data/jobs.watch.json` toutes les dix secondes. Le curseur Telegram et l'état
des incidents sont conservés séparément dans `data/jobs.telegram.json`.
Ces fichiers ne font pas partie de l'archive de sauvegarde SQLite.

Un verrou empêche deux instances locales du listener. Ne pas utiliser un autre
programme appelant `getUpdates` avec ce bot en parallèle. Un webhook existant
est refusé et jamais supprimé automatiquement.

Le curseur est enregistré avant de tenter une réponse ; les avis d'incident
sont également enregistrés avant envoi. Une livraison incertaine n'est donc
pas réessayée automatiquement au redémarrage. Si une réponse manque, envoyer
de nouveau `/status`. Un état local corrompu ou lié à une autre destination
provoque un arrêt, sans effacement automatique.

Références : [réception Telegram](https://core.telegram.org/bots/api#getupdates)
et [menu des commandes](https://core.telegram.org/bots/api#setmycommands).
