# Telegram : alertes, candidatures et état du radar

Disponible sur ce poste depuis le 24 septembre 2026.

## Alertes et boutons de candidature

Les nouvelles alertes utilisent une carte HTML : poste et entreprise, lieu,
dates connues, expérience, score visuel et extrait de la description employeur.
Les textes employeur sont échappés et raccourcis avant formatage.

Depuis le lot 55, la carte affiche **Missions · extraits** lorsqu'une rubrique
de missions est reconnue chez DRW, IMC, HSBC professionnels, Jump Trading,
Goldman Sachs professionnels, Citi, Deutsche Bank, Morgan Stanley, Barclays
et, depuis le lot 67, BNP Paribas : jusqu'à trois
extraits dans la langue de l'annonce, limités à 240 caractères chacun avec
une ellipse si nécessaire. Sinon, **Extrait de description** conserve le repli
habituel. Le dashboard montre les extraits complets et la rubrique d'origine.
Les messages déjà reçus ne sont pas réécrits et aucune ancienne alerte n'est
renvoyée à cause de cette évolution de présentation.

- **↗ Voir l’offre · Postuler** ouvre le lien employeur. L’ouverture ne change
  pas le suivi et n’envoie aucune candidature.
- **✓ J’ai postulé** confirme que vous avez envoyé votre candidature. Le statut
  devient **Postulé** (`Applied`), avec la date du jour à Paris si aucune date
  n’existait. Le bouton affiche ensuite **✅ Postulé**.

Cette confirmation exige le service `trading-radar telegram` actif avec
`TELEGRAM_CONTROL_ENABLED=true`, le même bot, le même chat privé et la même base
que le collecteur et le dashboard. Seul le destinataire configuré peut agir :
les boutons sont signés pour cette destination et cette offre. Les commandes
restent consultatives ; seuls ces boutons modifient les candidatures.

La modification et son historique sont atomiques, même pendant une collecte.
Un nouveau clic est sans effet si le statut est déjà `Applied`. Les étapes
ultérieures ou finales sont conservées, ainsi que les notes, contacts, actions
et dates déjà enregistrées. Une base momentanément occupée produit une demande
de réessai ; aucun succès n’est annoncé avant la validation de l’enregistrement.
Si l’accusé Telegram échoue après enregistrement, un nouveau clic reste sûr.

Dans le dashboard ouvert avec `--edit-applications`, le statut, les filtres et
le compteur se synchronisent sous dix secondes lorsque la page est visible.
Un formulaire ouvert conserve son brouillon et demande une relecture en cas de
changement externe. Les offres et l’état des sources exigent encore un rechargement.
Après mise à jour du serveur, recharger une fois les anciens onglets.

Les anciennes alertes, listes `/top`, `/new` et récapitulatifs restent tels quels.
Le nouveau format et les boutons s’appliquent aux alertes individuelles à venir.
Les anciens boutons restent utilisables tant que l’offre existe et que le token
du bot et le chat configuré n’ont pas changé.

Références : [boutons Telegram](https://core.telegram.org/bots/api#inlinekeyboardbutton),
[réponse aux clics](https://core.telegram.org/bots/api#answercallbackquery).

## Utilisation

Dans le chat privé avec `@ImmortalTradingBot` :

- `/status` affiche l'activité du collecteur, le dernier cycle terminé, la santé
  des sources et le nombre d'alertes envoyées ou à vérifier.
- `/help` affiche l'aide ; `/start` affiche également cette aide.
- `/top` affiche jusqu'à cinq offres à examiner, triées par score décroissant,
  puis découverte la plus récente.
- `/new` affiche jusqu'à cinq offres découvertes par le radar depuis 24 heures,
  les plus récentes en premier. Ce n'est pas leur date de publication employeur.

### Critères des listes `/top` et `/new`

Les listes utilisent le seuil des alertes (70/100 sur ce poste), avec un minimum
de 1 pour écarter les offres exclues même si le seuil est réglé à zéro. Elles
retiennent les statuts `New`, `Reviewing` et `To Apply`. Les candidatures déjà
envoyées ou terminées sont écartées, ainsi que les offres inactives, expirées
ou avec une échéance connue dépassée ou ambiguë.

La source doit être activée, avoir réussi depuis 24 heures et ne pas avoir un
échec plus récent. Chaque fiche doit également avoir été vérifiée depuis
24 heures. Une source à jour ne suffit donc pas à rafraîchir artificiellement
une ancienne fiche. Les données indisponibles produisent un message explicite,
jamais une liste partielle présentée comme complète.

Les dates et heures sont en UTC ; une échéance sans heure reste affichée avec
son heure et son fuseau inconnus. Elle est écartée lorsque son jour précède le
jour UTC du rapport. L'absence de deadline n'est pas une garantie d'ouverture.
Le minimum d'expérience affiché peut rester inconnu ou dépasser deux ans : le
classement reste un outil de tri, à vérifier sur le site employeur.

Chaque commande produit un seul message, avec le nombre affiché et le nombre
total de correspondances. De longs liens peuvent réduire le nombre affiché
en dessous de cinq. Un lien dépassant 700 unités UTF-16 est omis explicitement,
jamais coupé ; seuls les liens HTTP(S) valides sans identifiants sont affichés.
Les notes personnelles et les coordonnées de recruteurs ne sont pas incluses.
Les listes `/top` et `/new` sont demandées à la main.

## Récapitulatif quotidien

- `/digest` affiche le réglage actuel et un aperçu à la demande. Cette commande
  n'active pas l'envoi automatique et ne consomme pas l'envoi quotidien.
- `/digest_on 09:00` active le récapitulatif à 9 h, heure de Paris.
  Toute heure au format `HH:MM` est acceptée ; par exemple `19:00`.
- `/digest_on` reprend l'horaire mémorisé, initialement `09:00`.
- `/digest_off` désactive seulement le récapitulatif. Les alertes d'offres,
  les avis d'incident et les commandes restent disponibles.

Le réglage est conservé dans le fichier d'état Telegram local. Sur une nouvelle
installation et pour un ancien fichier d'état, le récapitulatif est **désactivé
par défaut**. L'activation commence au prochain horaire à venir, sans envoi
immédiat rétroactif. Un changement d'horaire ne permet pas de renvoyer le
récapitulatif d'une date déjà tentée.

Le message reprend les découvertes des 24 heures précédant son exécution,
avec les mêmes critères que `/new`, et le nombre de sources à jour. Un jour
sans offre correspondante reste signalé par un message explicite. Les dates
des fiches restent en UTC ; l'horaire de programmation est en Europe/Paris.

Le service vérifie l'horaire environ toutes les minutes. Il peut rattraper un
créneau manqué pendant les quatre heures suivantes, y compris après minuit.
Au-delà, le créneau est ignoré ; aucun empilement des jours manqués. Une coupure
du PC ou d'Internet empêche toujours le fonctionnement normal.

Une seule tentative automatique est enregistrée par date de créneau **avant**
l'appel Telegram. Un échec ou une livraison incertaine ne provoque pas de
réexpédition automatique ce jour-là, y compris après redémarrage. La « dernière
tentative » affichée n'est donc pas une preuve de réception : utiliser `/digest`
pour demander à nouveau un aperçu.

Les changements d'heure utilisent le fuseau `Europe/Paris`. La dépendance
verrouillée `tzdata` fournit notamment les règles sur Windows, où cette base
n'est pas disponible par défaut pour Python.
Si l'heure choisie tombe dans l'heure inexistante du printemps, elle est décalée
d'une heure réelle locale (02:30 devient 03:30). Lors du retour à l'heure d'hiver,
la première occurrence est retenue ; la seconde ne provoque pas un autre envoi.

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
