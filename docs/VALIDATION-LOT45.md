# Lot 45 — Offres consultables dans Telegram

Livré et installé le **24 septembre 2026**, commit applicatif `645e2be`.

## Résultat

- `/top` : jusqu'à cinq offres à examiner, classées par score puis découverte.
- `/new` : jusqu'à cinq offres découvertes dans les dernières 24 heures,
  les plus récentes en premier ; la publication employeur reste distincte.
- Chaque fiche affiche entreprise, titre, lieu, score, minimum d'expérience
  reconnu, dates de découverte/vérification, échéance et lien complet.
- Seuil configuré des alertes, sources et fiches récentes, suivi encore à
  examiner. Candidatures déjà envoyées, offres expirées et deadlines dépassées
  ou ambiguës écartées. Le détail des critères figure dans le
  [guide Telegram](TELEGRAM-CONTROL.md).

Le lecteur validé du dashboard devient une fonction partagée ; ses contrôles
de schéma, cohérence, intégrité et limite de 5 000 offres sont conservés.
Les commandes ne migrent pas la base, ne changent aucun score et n'écrivent
aucune candidature. Aucun digest automatique ni bouton de modification ajouté.

## Tests

Paquet Windows non éditable : **2 761 tests réussis**, couverture **96 %**.
Ruff vérifie 190 fichiers ; mypy vérifie 69 modules applicatifs.
La [CI du commit 645e2be](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35995857055)
réussit également sur **Python 3.11 à 3.14 : 2 761 tests par version**,
couverture 96 %, contrôles Ruff et mypy réussis.
Le build Docker et l'exercice de reprise réussissent sous UID 10001, avec
onze tables synthétiques restaurées identiques.
Les 41 nouveaux cas couvrent notamment :

- Tri et limites des deux listes, distinction découverte/publication.
- États de candidature, sources désactivées ou en échec, vérification par fiche,
  données futures et échéances précises ou ambiguës.
- Minimum d'expérience zéro, inconnu ou supérieur à deux ans.
- Conservation des onze tables lors de la consultation.
- Destinataire privé autorisé, absence de lecture pour un autre expéditeur,
  absence de replay d'une même commande.
- Corps longs et emojis sous la limite Telegram, URL entière ou omission
  explicite, absence de notes privées dans les réponses.
- Base absente ou données incohérentes : erreur explicite, aucune création
  de base et aucune liste partielle.

Les premiers échecs ciblés provenaient des fixtures : l'upsert de collecte
préserve la découverte et rouvre les offres, tandis que les identifiants
employeur identiques fusionnent les clones. Les scénarios historiques ont été
initialisés explicitement ; les règles de stockage de production ne changent pas.

## Déploiement et preuves locales

Sauvegarde cohérente vérifiée à **11 h 55 UTC**, puis arrêt effectif des trois
processus, reconstruction du paquet avec dépendances verrouillées et relance.
Les trois services sont en cours d'exécution et le dashboard répond HTTP 200.

À **11 h 56 UTC**, l'API Telegram confirme le menu privé
`status`, `top`, `new`, `help`. Le signal du collecteur est récent.
Le paquet réellement installé génère :

- `/top` : cinq affichées sur 123 correspondances, 2 311 unités UTF-16.
- `/new` : cinq affichées sur 17 correspondances, 1 811 unités UTF-16.

Ces comptes sont une observation datée : ils changent avec les collectes et
la fraîcheur. Les exemples sont générés localement, sans envoi de test ajouté
dans le chat. Aucune commande `/top` ou `/new` envoyée depuis le téléphone
n'est encore revendiquée. Les commandes précédentes `/status` et `/help`
ont bien été traitées par le service à 11 h 46 UTC.

Preuves privées dans `data/windows-service/` : `lot45-tests.txt`,
`lot45-tests.xml`, `lot45-backup.json`, `lot45-smoke.json` et les deux
`lot45-installed-*.txt`. Le token et la destination ne figurent pas dans ces
rapports ni dans Git.
Les journaux GitHub sont conservés localement dans les `ci-lot45-*.json`.

## Limites conservées

Pas de garantie d'éligibilité ou d'exhaustivité ; chaque offre reste à vérifier
chez l'employeur. Les commandes demandent un PC connecté et une session ouverte.
Les incidents de certaines sources, la surveillance externe et la sauvegarde
distante restent des travaux séparés.
