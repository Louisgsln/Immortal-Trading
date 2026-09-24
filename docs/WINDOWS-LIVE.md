# Exploitation continue sur le PC Windows

Mise en service commencée le **24 septembre 2026**. Le radar utilise Python
directement sur Windows et le Planificateur de tâches. Le dashboard et le
collecteur partagent ainsi la base existante `data/jobs.db`, ses candidatures et
ses historiques. Docker reste validé pour un futur déploiement distinct.

## Services installés

| Tâche Windows | Déclenchement | Rôle |
| --- | --- | --- |
| `Immortal-Trading-watch` | Ouverture de session FlowUP | Collecte continue selon les intervalles configurés |
| `Immortal-Trading-dashboard` | Ouverture de session FlowUP | Dashboard éditable sur `http://127.0.0.1:8765` |
| `Immortal-Trading-telegram` | Ouverture de session FlowUP | Commandes privées et surveillance des incidents |
| `Immortal-Trading-backup` | Chaque jour à 03 h 15, heure Windows | Sauvegarde ZIP cohérente, puis vérification |

Les tâches fonctionnent avec les droits ordinaires de l’utilisateur, via le
`pythonw.exe` de base et `scripts/windows_entry.py`, sans fenêtre de console.
Ce lanceur charge le paquet installé non éditable et ses dépendances verrouillées
depuis `data/service-venv/Lib/site-packages`. Il évite le processus intermédiaire
du lanceur de virtualenv Windows : l’arrêt d’une tâche doit arrêter le service.
Les tâches longues n’ont pas de limite de durée ; un échec entraîne une reprise
après une minute, au maximum 999 reprises. Un verrou par service et l’option
`IgnoreNew` empêchent les doubles lancements par ces tâches.

Le PC doit rester allumé et connecté ; la veille sur secteur est déjà désactivée.
Un arrêt puis redémarrage du dashboard a été vérifié, avec libération du port
et réponse HTTP 200 après reprise. L’ouverture de session reste nécessaire après un redémarrage. Verrouiller la
session est compatible avec le fonctionnement ; fermer la session, éteindre le
PC ou interrompre Internet affecte la surveillance. Aucune reprise après un vrai
redémarrage ni observation de 24 heures n’est encore revendiquée.

## Telegram

Le bot `@ImmortalTradingBot` est validé. Son token est dans `.env`, ignoré par Git.
**Alertes activées le 24 septembre à 08 h 43**, après le premier contact privé
de l’utilisateur et l’accusé positif de Telegram pour le message de test.
La destination privée est configurée localement, sans publication de son identifiant.

Depuis le lot 44, `/status` et `/help` sont disponibles dans ce chat.
Les alertes d'offres ont des libellés français. Le service Telegram indépendant
signale les incidents persistants avec espacement des messages ; il ne peut pas
signaler une coupure de tout le PC. Voir [TELEGRAM-CONTROL.md](TELEGRAM-CONTROL.md).

`ALERTS_ENABLED=true` est configuré et la tâche du collecteur a été relancée.
Son processus lit la configuration au lancement. Pour une modification future,
attendre la fin effective de l’ancien processus avant de relancer : l’état Ready
du Planificateur peut précéder brièvement la libération du verrou Windows.

Le seuil actuel est 70/100, pour les nouvelles offres, réouvertures et changements
jugés importants. Pas de réexpédition automatique du catalogue antérieur ni des
changements collectés pendant la désactivation. Les rappels de deadline restent
désactivés. Une livraison incertaine demande une décision opérateur ; voir
[ALERTS.md](ALERTS.md).

Un token communiqué dans une conversation doit être renouvelé dans BotFather,
puis remplacé localement. Ne pas le placer dans les arguments des tâches ni
publier `.env`. Les journaux du lanceur masquent aussi sa valeur.

## Contrôle et arrêt

Depuis PowerShell, dans le dépôt :

```powershell
Get-ScheduledTask -TaskName 'Immortal-Trading-*'
Get-ScheduledTaskInfo -TaskName 'Immortal-Trading-watch'
Get-Content data/windows-service/watch.log -Tail 20
data/service-venv/Scripts/python.exe -m trading_radar health
```

Le code de tâche `267009` signifie qu’elle s’exécute encore. Cela ne prouve pas
à lui seul le succès des collectes : consulter les événements `source_success`,
les bilans de scan et la fraîcheur des sources. Les sources en échec restent
visibles dans le diagnostic ; le radar ne garantit pas l’accès à chaque portail.

Pour arrêter la collecte et empêcher son retour à la prochaine connexion :

```powershell
Disable-ScheduledTask -TaskName 'Immortal-Trading-watch'
Stop-ScheduledTask -TaskName 'Immortal-Trading-watch'
```

Pour la reprendre :

```powershell
Enable-ScheduledTask -TaskName 'Immortal-Trading-watch'
Start-ScheduledTask -TaskName 'Immortal-Trading-watch'
```

Ne pas lancer un second watcher manuel ou Docker sur la même base. Le verrou
de scan existant protège les écritures, mais un seul processus permanent est prévu.

## Sauvegardes et journaux

Les archives vérifiées vont dans `data/backups/scheduled-*.zip`. La tâche reprend
une occurrence manquée lorsque ses conditions permettent son exécution. Aucun
nettoyage automatique n’est appliqué. Vérifier l’espace disque et examiner
`backup plan` avant toute politique de suppression.

Ces archives sont sur le même PC : **la copie sur un stockage distinct reste
à configurer**. Elles contiennent des données personnelles. Voir [BACKUPS.md](BACKUPS.md).

Chaque service conserve un journal de 10 Mo et trois archives dans
`data/windows-service/`. Le nom des fichiers PID ne constitue pas une preuve
qu’un processus est vivant ; vérifier les tâches et les événements récents.

## Installation et mises à jour

`scripts/install_windows_tasks.ps1` enregistre les quatre tâches et refuse
d’écraser des tâches existantes. Le lanceur est `scripts/windows_service.py`.
Avant une mise à jour du paquet installé, arrêter les trois tâches longues,
sauvegarder la base, reconstruire `data/service-venv` avec le lock, vérifier puis
reprendre les tâches. Une modification de `src/` seule ne met pas à jour ce paquet.

## Premier cycle observé

Le 24 septembre, de 08 h 30 à 08 h 37 : 24 sources exécutées, 22 réussies,
720 fiches reçues, 33 nouvelles, 37 modifications, aucune fermeture ni alerte.
BNP refuse l’endpoint dans sa politique robots ; Deutsche Bank renvoie un listing
non conforme. Les contrôles restent actifs et leurs snapshots ne sont pas importés.
Le cycle suivant a également rencontré une pagination UBS répétée ; l’état des
sources reste à surveiller. Ce premier passage ne valide pas 24 heures d’exploitation.

Les sept tests du lanceur et les 42 tests ciblés du serveur éditable passent.
Deux passages complets Windows ont chacun rencontré un refus HTTP intermittent
`WinError 10053` dans un test existant de rejet des requêtes du dashboard
(`cross_site_requests`, puis `duplicate_headers`). Aucun changement du serveur
HTTP n’était inclus dans cette première mise en service. Le lot 44 corrige
ces refus par une lecture bornée du corps restant : le passage complet Windows
réussit désormais, avec 2 720 tests. Voir [VALIDATION-LOT44.md](VALIDATION-LOT44.md).

La [CI du déploiement Windows](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35965637822)
réussit sur Python 3.11 à 3.14 : **2 659 tests par version**, couverture applicative
96 %. Build Docker et restauration des onze tables synthétiques réussis sous
UID 10001. Ruff vérifie 184 fichiers et mypy 71 fichiers lors du contrôle local.
La sauvegarde avec le lanceur définitif se termine avec le code zéro à 08 h 45.
