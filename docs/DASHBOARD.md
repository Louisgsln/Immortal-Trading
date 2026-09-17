# Dashboard local en lecture seule

Le mode de consultation décrit ici reste disponible. Depuis le lot 25, l'option
`dashboard serve --edit-applications` permet aussi [l'édition locale du suivi](DASHBOARD-EDITING.md),
avec historique et détection des conflits. Elle est distincte de l'export HTML.

Le dashboard regroupe les offres, le suivi des candidatures, les échéances et la santé
des sources, ainsi que les tendances historiques, dans un fichier HTML autonome. Il s'agit d'un **instantané** : les changements
ultérieurs de la base ou de la configuration nécessitent un nouvel export.

## Exporter et ouvrir

```powershell
trading-radar dashboard export data/dashboard.html
trading-radar dashboard export data/dashboard-archive.html --config-dir config --history-dir data/health-history
trading-radar dashboard export data/dashboard.html --overwrite
```

Ouvrir ensuite le fichier HTML dans un navigateur. Les styles, le code d'affichage et les
données sont inclus dans le fichier ; aucun CDN, compte ou service web n'est nécessaire.
La commande ne lance ni serveur, ni collecte, ni watcher. Elle n'envoie aucune alerte et
ne crée aucune candidature. Les filtres du navigateur modifient uniquement la vue locale.

Le nom de destination doit se terminer par `.html`. Un fichier existant est protégé par
défaut ; `--overwrite` autorise explicitement son remplacement. Cette option ne permet
pas d'écraser la base configurée, ses fichiers auxiliaires, un lien symbolique ou un fichier
du dossier de références synchronisées `sources/`. Une erreur de lecture de la base
empêche la publication du dashboard.

Un export réussi renvoie un résumé JSON avec la destination, l'instant de génération,
le nombre d'offres et la taille du fichier. Le code de sortie vaut `0` en cas de réussite
et `1` en cas d'erreur de configuration, de données ou de destination. Les arguments
invalides sont rejetés par le CLI avec le code `2`.

L'instant de génération est affiché en tête du dashboard. Les dates doivent toujours être
interprétées avec leur fuseau : une date limite sans heure précise ne constitue pas une
heure d'expiration garantie. La fraîcheur d'une source porte sur sa dernière collecte
réussie, indépendamment de l'ancienneté des offres qu'elle contient.

## Prévisualiser sur le poste

```powershell
trading-radar dashboard serve
trading-radar dashboard serve --port 8765 --config-dir config --history-dir data/health-history
```

Ouvrir `http://127.0.0.1:8765` dans un navigateur et arrêter le serveur avec `Ctrl+C`.
Le serveur écoute uniquement sur la boucle locale `127.0.0.1` ; il ne propose aucune option
d'exposition réseau. Il sert un instantané en mémoire, sans créer de fichier HTML ni
d'archive de santé. Recharger la page conserve cet instantané : relancer la commande pour
actualiser les données.

Ce serveur ne parcourt aucun répertoire et ne propose aucune écriture. Il refuse les
requêtes de modification et les accès identifiés comme provenant d'un autre site. Un
diagnostic d'erreur métier peut y être affiché pour expliquer pourquoi les offres sont
indisponibles ; `export` refuse quant à lui de publier un nouveau fichier dans ce cas.

## Lire le diagnostic

La vue **Offres** permet de rechercher un poste, une entreprise ou une localisation,
de filtrer par entreprise, score, activité, expérience et statut de candidature, puis de trier les
résultats. Elle affiche les offres actives par défaut. Ouvrir le détail d'une ligne pour
consulter la description, la décomposition du score, le suivi et les liens d'origine.
La vue **Candidatures** rassemble le suivi ; la vue **Santé des sources** expose les
dernières observations et les rapports de santé conservés.

Depuis le lot 35, la liste et le détail affichent le **minimum d’expérience reconnu**.
Le filtre distingue **Minimum 0–2 ans**, **Minimum >2 ans** et **Minimum non reconnu**.
Il prend le plus grand minimum identifié dans la description et les données structurées,
en réutilisant le parseur du score. Un zéro structuré est conservé ; un titre junior
ne crée pas de minimum chiffré. Les préférences reconnues sont écartées.

Cet indicateur ne décide pas de l’éligibilité : une fourchette 2–5 ans a un minimum
de deux ans, sans garantir qu’un candidat avec deux ans sera retenu. « Non reconnu »
ne signifie ni absence d’exigence ni zéro expérience. Les formulations ambiguës peuvent
rester inconnues ; consulter les qualifications et alternatives de l’annonce officielle.
Le filtre ne change aucun score et se combine aux autres filtres ; Réinitialiser
rétablit toutes les catégories. Les anciens jeux de données sans cet indicateur sont
affichés comme non reconnus. Voir l’[audit des 814 offres](EXPERIENCE-VISIBILITY-LOT35.md).

Le [lot 37](VALIDATION-LOT37.md) élargit le parseur aux fourchettes explicites sans
signe `+` associées à l’expérience du candidat. Le même minimum alimente le score
et l’indicateur. Préférences, profils usuels et alternatives restent protégés ;
les formulations `years in…` sans `experience` restent hors de cette extension.

Le [lot 39](VALIDATION-LOT39.md) couvre désormais certaines qualifications
`N–M years in…` et `N+ years in…`, dans les rubriques et domaines professionnels
audités. Sept indicateurs auparavant inconnus deviennent explicites, sans changement
des scores totaux. Les exigences académiques ou professionnelles ambiguës de type
`track record` demandent encore un traitement distinct ; voir l’[audit de leur
provenance](AMBIGUOUS-EXPERIENCE-LOT39.md).

La vue **Tendances** présente les 7, 30 ou 90 derniers jours UTC (30 par défaut).
Elle distingue premières détections locales, mises à jour, recalculs, fermetures,
réouvertures, scans et échecs de sources. Le graphique montre au maximum les 14 derniers
jours avec détection ; le journal liste tous les jours avec activité de la période.
Les jours sans activité sont omis dans cette vue et explicitement inclus dans le JSON
de la commande `trends`. Voir les définitions et limites dans [TRENDS.md](TRENDS.md).

Les compteurs utilisent toutes les lignes de l'instantané, indépendamment des filtres.
Les actions échues sont les dates de prochaine action inférieures ou égales au jour UTC
de génération, y compris lorsqu'une candidature est clôturée. Le suivi en cours inclut
le statut `Offer`. Un indicateur d'expiration enregistré provient de la dernière
observation de l'offre ; il ne remplace pas la lecture de l'échéance et de sa précision.

Une page exportée ne devient pas automatiquement plus récente lorsqu'on la recharge.
La santé affichée décrit l'état observé lors de la génération. Une collecte réussie avec
zéro offre peut être saine ; une source jamais collectée ou périmée exige une vérification
du collecteur. Le dashboard ne mesure pas la disponibilité du réseau ou de Telegram.

Les offres et candidatures sont lues ensemble dans une transaction SQLite. Le contrôle de
santé, les tendances et les archives sont des observations séparées : pendant une collecte concurrente,
leur état peut donc différer légèrement. Les détails conservent les dates de dernière
observation pour permettre cette lecture.

L'historique de santé vient du dossier indiqué par `--history-dir`. Utiliser un dossier
propre à la base et à l'environnement consultés. Il n'est pas alimenté automatiquement
par l'export : [monitor record](MONITORING.md) enregistre explicitement un diagnostic.
Des captures utilisant des seuils de fraîcheur différents peuvent expliquer une évolution
de statut sans changement du collecteur.

Une erreur de l'historique de santé ou des tendances est signalée sans empêcher la consultation des offres. En
revanche, une base métier absente, corrompue, incompatible ou contenant des enregistrements
incohérents bloque l'export. La limite actuelle est de 5 000 offres : au-delà, la génération
échoue explicitement et ne présente pas une liste tronquée comme si elle était complète.

## Données locales

Le fichier contient les informations affichées même lorsqu'un filtre masque des lignes.
Il contient notamment les notes et informations de recruteur du suivi des candidatures :
le conserver comme un export privé. Les secrets de configuration et identifiants Telegram
ne font pas partie de cet export. L'ouverture d'un lien
vers une offre consulte le site concerné ; le dashboard n'effectue aucune requête de
collecte et ne soumet aucun formulaire de candidature.

La lecture SQLite ne crée ni ne migre la base. Les données validées dans le journal WAL
sont prises en compte. La génération ne change ni les statuts des candidatures ni ceux
des alertes. Une alerte incertaine reste à examiner via les commandes documentées dans
[ALERTS.md](ALERTS.md).

Pour modifier le suivi, utiliser [les commandes de candidature](APPLICATIONS.md), puis
générer un nouvel instantané. Pour préserver l'ensemble de la base et de ses historiques,
utiliser une [sauvegarde SQLite vérifiée](BACKUPS.md) : le HTML est une vue de consultation,
pas une sauvegarde restaurable.
