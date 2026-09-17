# Consulter et résoudre les alertes

Les commandes `alerts` gèrent la file locale. Elles n'utilisent ni réseau ni Telegram, même si les alertes générales sont activées. Une décision `retry` peut permettre un envoi **lors d'un prochain scan activé** ; elle n'envoie rien immédiatement.

## Inspection

Depuis la racine, utiliser `trading-radar` ou `.\.venv\Scripts\trading-radar.exe` :

```powershell
trading-radar alerts list
trading-radar alerts list --status pending
trading-radar alerts list --all --limit 50 --offset 50
trading-radar alerts show ALERT_ID
trading-radar alerts history ALERT_ID
```

La liste par défaut affiche les états `unknown` et `sending`. `--all` et `--status` sont exclusifs. Le résumé compte tous les états, tandis que `matching` compte les lignes du filtre avant pagination. Les alertes sont ordonnées par identifiant croissant, par pages de 50 par défaut.

`show` affiche notamment l'identifiant, la clé d'événement, l'état, les tentatives, le dernier type d'erreur, l'éventuel `sent_at` et la **révision actuelle**. Titre, score, statut de candidature et état de l'offre viennent des données actuelles : il ne s'agit pas d'une copie du message Telegram historique.

| État | Interprétation |
| --- | --- |
| `pending` | En attente ; livraison possible lors d'un passage autorisé |
| `sending` | Tentative engagée ; après interruption, résultat possiblement inconnu |
| `sent` | Accusé positif traité, ou réception confirmée explicitement par l'opérateur |
| `unknown` | Résultat non déterminé, notamment timeout ou réponse ambiguë |
| `suppressed` | Alerte abandonnée ou devenue inéligible ; pas de reprise automatique |

`sending` ne prouve pas qu'un processus tourne encore. Si un scan détient le verrou, la décision opérateur est refusée jusqu'à sa fin. Aucune durée écoulée ne suffit à présumer qu'un message n'a pas été reçu.

## Décisions explicites

Remplacer `ALERT_ID` et `REVISION` par les valeurs de `show` ou `list`. Choisir **une** action selon ce qui a été vérifié :

```powershell
trading-radar alerts resolve ALERT_ID --decision received --revision REVISION --reason "Message retrouvé dans Telegram"
trading-radar alerts resolve ALERT_ID --decision dismiss --revision REVISION --reason "Information devenue inutile"
trading-radar alerts resolve ALERT_ID --decision retry --revision REVISION --reason "Vérification effectuée, nouvelle tentative souhaitée"
```

| Décision | États autorisés | Résultat |
| --- | --- | --- |
| `received` | unknown, sending | Marque sent, sans envoi ni nouvelle tentative |
| `dismiss` | pending, unknown, sending | Marque suppressed |
| `retry` | unknown, sending | Remet pending, sans envoi immédiat |

Les états sent et suppressed restent terminaux pour cette interface. Un état pending n'a pas besoin d'être remis pending. Pour annuler une remise en attente encore non traitée, relire sa révision puis utiliser dismiss.

**Une reprise après un résultat incertain peut créer un doublon si le message avait déjà été reçu.** La décision et son motif documentent le choix de l'opérateur ; le logiciel ne peut pas vérifier lui-même la boîte Telegram. Les messages incertains ne sont jamais retentés automatiquement.

Le motif doit contenir 1 à 2 000 caractères après retrait des espaces extérieurs. Il est conservé localement dans l'historique ; ne pas y saisir de token ou de mot de passe. Si l'alerte a changé depuis sa consultation, la commande refuse la révision périmée : relire la fiche et réévaluer la décision. Cela vaut aussi si l'état est revenu à unknown après une nouvelle tentative.

## Revalidation avant un envoi

La remise en attente conserve la même clé d'événement. Le prochain scan ne livre que si les alertes générales sont activées et Telegram configuré. Pour les rappels de deadline, leur activation distincte doit aussi être vraie.

Les contrôles habituels restent appliqués : offre active, échéance non expirée, score suffisant ; pour les rappels, fenêtre actuelle, deadline inchangée, observation récente et candidature toujours éligible. Une candidature passée à Applied après une décision retry bloque donc le rappel. Le message éventuel reflète l'offre actuelle.

Le réglage des alertes et celui des rappels restent désactivés dans la configuration actuelle. Les commandes de gestion ne les modifient pas.

## Historique et compteurs

L'historique conserve chaque transition automatique et chaque décision opérateur : heure UTC, acteur `system` ou `operator`, décision, motif éventuel et états complets avant/après. La révision est l'identifiant de la dernière entrée de cette alerte ; elle peut avoir des sauts car les entrées sont numérotées pour toute la base. La révision 0 signifie qu'aucune transition n'est encore historisée.

Une transition et son historique réussissent ou échouent ensemble. Le même verrou protège scans, candidatures et décisions opérateur. Répéter une transition système strictement identique ne crée pas d'entrée supplémentaire ; répéter une décision avec une ancienne révision est refusé.

À partir du lot 18, `attempts` augmente uniquement au passage vers sending : il compte les tentatives engagées, pas tous les changements d'état. Un arrêt juste avant l'appel réseau peut donc laisser une tentative comptée sans message envoyé. Une décision manuelle ne change pas ce compteur.

`sent_at` est renseigné lorsque le programme traite un accusé de livraison positif. Confirmer received après un résultat inconnu ne fabrique pas un instant de livraison : `sent_at` reste inconnu et l'heure de confirmation se trouve dans l'historique opérateur.

Le schéma SQLite passe de 3 à 4 pour ajouter `alert_history` et son index. Les anciennes alertes gardent leurs données et compteurs, y compris l'ancienne convention de comptage des transitions ; leur passé n'est pas reconstruit. Utiliser la version actuelle du programme avec cette base. Un schéma plus récent est refusé avant toute migration.

## Accusés Telegram

Le client exige un objet JSON avec un booléen `ok` valide. Une réponse illisible, un champ manquant, une valeur comme `"true"`, un statut 2xx inattendu, une redirection ou une erreur serveur sont classés incertains. Un rejet explicite reste retentable selon la logique existante. Les URLs Telegram et tokens ne sont pas enregistrés dans les erreurs de transport.

## Démonstration et limites

Toutes les commandes acceptent `--demo` et `--config-dir`. La base démo reste distincte de la base réelle ; les scans démo n'y créent pas d'alertes à livrer. Les parcours avec alertes synthétiques sont couverts par les tests sur bases temporaires.

La commande ne consulte pas l'historique Telegram, ne garantit pas une livraison exactement une fois et ne restaure pas une ancienne copie du message. L'historique local n'est pas un journal d'audit protégé contre une modification manuelle du fichier SQLite. Sauvegardes/restauration et validation d'exploitation prolongée sont les prochaines étapes.
