# Trading Job Radar

Radar personnel d'offres Trading / Global Markets / Quant Trading, orienté vers une prise de poste junior en 2027. Le premier lot fonctionne de bout en bout : collecte publique → normalisation → exclusions → score explicable → déduplication → SQLite → CSV et Telegram optionnel.

Le master prompt original est conservé localement dans `docs/`, hors Git car il contient le profil personnel du candidat. La [feuille de route](docs/ROADMAP.md) suit les tâches et distingue ce qui est livré des phases suivantes. Les fichiers synchronisés dans `sources/` sont des références en lecture seule et ne sont pas publiés.

Le deuxième lot ajoute **Deutsche Bank, Morgan Stanley, Citi et Barclays via Workday**. La [couverture des sources](docs/SOURCES.md) précise les portails vérifiés, les filtres et les limites de collecte. Les annonces sont recherchées et décrites en direct ; il s'agit d'un périmètre Trading ciblé, pas de l'ensemble des offres de chaque banque.

Le troisième lot ajoute **Goldman Sachs**, via sa recherche publique et ses fiches détaillées : 70 offres importées, base portée à 413 offres. Le connecteur Oracle pour JPMorgan est préparé et testé hors réseau ; cette source reste désactivée après une réponse HTTP 403 du portail depuis ce poste. `doctor` affiche désormais aussi les sources désactivées et leur motif. Voir le [bilan du lot 3](docs/VALIDATION-LOT3.md).

Le quatrième lot étend Goldman aux **programmes campus** et ajoute le connecteur **BNP Paribas** : recherche HTML publique, pagination et fiches structurées. UBS et Société Générale sont repérés dans la configuration, désactivés en attendant leurs connecteurs. Voir le [bilan du lot 4](docs/VALIDATION-LOT4.md).

Le cinquième lot active **UBS étudiants/graduates** : lecture du portail public avec une session anonyme, pagination complète du tableau et descriptions détaillées. Le portail UBS professionnel reste hors périmètre. Voir le [bilan du lot 5](docs/VALIDATION-LOT5.md).

Le sixième lot active **Société Générale**, à partir des répertoires publics français et anglais. Les références communes sont réunies avant lecture des fiches ; missions, exigences et dates de début affichées sont conservées. Voir le [bilan du lot 6](docs/VALIDATION-LOT6.md).

Le septième lot ajoute **Crédit Agricole CIB** et **HSBC étudiants/graduates** : pagination des catalogues publics, détails complets, lieux multiples et dates explicites. Le score exploite aussi les contrats de stage et l'expérience minimale structurée pour éviter les faux positifs. Voir le [bilan du lot 7](docs/VALIDATION-LOT7.md).

Le huitième lot ajoute **Macquarie** et **Nomura campus**. Macquarie utilise la recherche Avature publique ; Nomura le tableau officiel des opportunités étudiantes. Les niveaux d'expérience publiés et les descriptions complètes alimentent le classement. Voir le [bilan du lot 8](docs/VALIDATION-LOT8.md).

Le neuvième lot ajoute **Optiver** : API publique paginée et fiches détaillées, avec contrôle des niveaux graduate/stage. Les programmes de découverte et inscriptions en vivier sont exclus de la priorité. **Citadel Securities reste désactivé**, son portail répondant HTTP 403 depuis cet environnement. Voir le [bilan du lot 9](docs/VALIDATION-LOT9.md).

Le dixième lot active **IMC et DRW**, via leurs tableaux Greenhouse publics vérifiés. Les descriptions complètes, contrats et débuts d'emploi explicites alimentent le classement ; les inscriptions en vivier et annonces marquées cachées sont écartées. Voir le [bilan du lot 10](docs/VALIDATION-LOT10.md).

Le onzième lot active **SIG / Susquehanna et Flow Traders**. SIG utilise son catalogue iCIMS/Jibe public ; Flow Traders étend le connecteur Greenhouse filtré. Les événements, fonctions opérationnelles et contradictions graduate/stage sont traités explicitement. Voir le [bilan du lot 11](docs/VALIDATION-LOT11.md).

Le douzième lot active **Jump Trading et XTX Markets** : 24 nouvelles fiches, soit 746 conservées au total. Chez XTX, le département et la rubrique des missions permettent de reconnaître un poste de développement des systèmes de trading sans attribuer ce rôle aux fonctions d'infrastructure générale. Voir le [bilan du lot 12](docs/VALIDATION-LOT12.md).

Le treizième lot étend **UBS et HSBC aux portails professionnels**, avec des sources distinctes des programmes campus. La collecte HSBC vérifie chaque fiche publique et écarte la division Wealth & Premier Banking. Le lecteur `robots.txt` applique désormais les règles de chemin les plus précises ; les titres Legal, COO et Business Manager sont exclus du classement prioritaire. Voir le [bilan du lot 13](docs/VALIDATION-LOT13.md).

Le quatorzième lot ajoute **Nomura professionnels**, via la recherche publique SuccessFactors et les descriptions intégrales. Les grades explicitement publiés et les minima d'expérience alimentent le score ; eTrading est inclus dans le filtre de titres. Voir le [bilan du lot 14](docs/VALIDATION-LOT14.md).

Le quinzième lot ajoute **l'audit de fraîcheur hors ligne** et actualise les quatre banques Workday. La comparaison de recherches supplémentaires conserve `trading` : aucune fiche supplémentaire évaluée ne passe les critères actuels, et la recherche Citi `structuring` dépasse le budget de résultats. Voir les mesures et limites dans le [bilan du lot 15](docs/VALIDATION-LOT15.md).

Le seizième lot ajoute le **suivi local des candidatures** : douze statuts, notes, recruteur, dates et prochaines actions, avec historique des modifications et export CSV enrichi. Goldman Sachs et Jane Street sont actualisés. Voir le [guide du suivi](docs/APPLICATIONS.md) et le [bilan du lot 16](docs/VALIDATION-LOT16.md).

Le dix-septième lot ajoute la **consultation des deadlines et les rappels J−7/J−3/J−1**. Les dates incomplètes restent distinctes des timestamps précis ; les rappels vérifient le statut de candidature, la fraîcheur et l'état de l'offre avant chaque envoi. La prévisualisation est disponible hors réseau, et l'envoi reste désactivé. Voir le [guide des échéances](docs/DEADLINES.md) et le [bilan du lot 17](docs/VALIDATION-LOT17.md).

Le dix-huitième lot ajoute la **gestion locale des alertes incertaines** : consultation, historique et décisions explicites avec contrôle de révision. Les reprises restent soumises aux contrôles de livraison ; aucune commande de gestion n'envoie de message. Voir le [guide des alertes](docs/ALERTS.md) et le [bilan du lot 18](docs/VALIDATION-LOT18.md).

Le dix-neuvième lot ajoute les **sauvegardes SQLite cohérentes avec WAL et la restauration vers une nouvelle base**. L'archive est vérifiée avant publication et avant récupération. L'exercice réel conserve les 811 offres et le contenu des 11 tables. Voir le [guide de récupération](docs/BACKUPS.md) et le [bilan du lot 19](docs/VALIDATION-LOT19.md).

Le vingtième lot ajoute les **dépendances verrouillées, le contrôle de santé et l'exercice de reprise en CI**. Trois sous-agents ont travaillé sur ces volets en parallèle. Le parcours de récupération est validé localement ; le build Docker reste à exécuter sur un hôte équipé. Voir le [guide d'exploitation](docs/OPERATIONS.md) et le [bilan du lot 20](docs/VALIDATION-LOT20.md).

Le vingt-et-unième lot ajoute **l'historique de santé, un cache conditionnel Workday optionnel et une extension ciblée des postes techniques Jump**. Les rapports sont conservés séparément de SQLite ; le cache reste en mémoire et exige une revalidation HTTP. Deux annonces supplémentaires sont reconnues dans le corpus Jump audité, sans priorité junior inventée. Voir [MONITORING.md](docs/MONITORING.md), [WORKDAY-CACHE.md](docs/WORKDAY-CACHE.md) et le [bilan du lot 21](docs/VALIDATION-LOT21.md).

## Démarrer sur ce poste

**WSL 2 et Docker local sont validés depuis le 23 septembre 2026** : image
construite, lancement et reprise testés sur huit offres synthétiques, onze tables
restaurées identiques. Voir la [validation Windows](docs/WINDOWS-DOCKER-SETUP.md).
Depuis le 24 septembre, la collecte continue et le dashboard fonctionnent via
des tâches Windows sur la base existante, avec sauvegarde quotidienne vérifiée.
L’activation Telegram attend le premier message privé au bot. Le PC doit rester
allumé, connecté et la session ouverte ; voir [l’exploitation Windows](docs/WINDOWS-LIVE.md).

Le lot 43 actualise **Barclays, Deutsche Bank, Morgan Stanley et Citi** :
14 nouvelles offres et huit mises à jour après revue, sauvegarde et répétition.
Sept grades seniors explicites sont reconnus. Le dashboard compte désormais
**246 pertinentes actives et 166 prioritaires**, sur 832 offres actives.
Neuf sources sont fraîches ; quinze restent à actualiser. Les annonces absentes
conservent leur ancienne date de vérification. Voir le [bilan du lot 43](docs/VALIDATION-LOT43.md).

Le lot 42 actualise **IMC, DRW, Flow Traders, Jump et XTX** : six nouvelles offres,
deux descriptions mises à jour et aucune fermeture déduite d’une absence.
Il portait le dashboard à **243 pertinentes actives et 162 prioritaires**. Cinq sources
avaient été rafraîchies, dix-neuf restaient à actualiser. Le changement de rubrique IMC conserve
son exigence de trois ans ; les refus HTTP du serveur de consultation sont fiabilisés
sous Windows. Voir le [bilan du lot 42](docs/VALIDATION-LOT42.md).

Le lot 41 ajoute la **provenance du champ d’expérience employeur** à 21 fiches
Crédit Agricole CIB et reconnaît les cinq ans requis par une offre Macquarie de
sales trading. Le classement corrigé compte **239 pertinentes actives et
160 prioritaires**. Ce travail utilise les captures conservées ; il ne renouvelle
pas la vérification des offres en ligne. Voir le [bilan du lot 41](docs/VALIDATION-LOT41.md).

Le lot 40 distingue **pratique académique et expérience professionnelle** sur
deux offres Jump auditées. Les preuves, leur cadre et l’extrait d’origine sont
visibles dans les fiches ; cinq ans de pratique industrie/académie ne deviennent
plus cinq années d’emploi. Classement conservé à **240 pertinentes actives et
161 prioritaires**. Voir le [bilan du lot 40](docs/VALIDATION-LOT40.md).

Le lot 39 reconnaît des exigences comme **« 3+ years in options trading »**.
Sept offres affichent désormais un minimum explicite de trois ou sept ans ;
leurs explications sont corrigées, avec **240 offres pertinentes actives et
161 prioritaires** conservées. Voir le [bilan du lot 39](docs/VALIDATION-LOT39.md).

Le lot 38 détecte les **stages explicites Jane Street même sans « Intern » dans
le titre** : six offres sortent du classement pertinent, avec un motif visible
dans les fiches. Le dashboard et le CSV comptent **240 offres pertinentes actives,
dont 161 prioritaires**. Voir le [bilan du lot 38](docs/VALIDATION-LOT38.md).

Le lot 37 reconnaît les **fourchettes d’expérience sans signe +** dans les
qualifications explicites, en préservant préférences et alternatives. Sept scores
sont corrigés ; le dashboard et le CSV reflètent **161 offres prioritaires actives**.
Voir le [bilan du lot 37](docs/VALIDATION-LOT37.md).

Le lot 36 valide **Docker Linux en CI** : build, commande installée et restauration
de onze tables réussis. Les **2 068 tests passent sur Python 3.11 à 3.14**, après
correction des imports pytest en installation propre. Rapports de CI conservés ;
voir le [bilan du lot 36](docs/VALIDATION-LOT36.md). WSL reste à activer sur le poste Windows.

Le lot 35 affiche le **minimum d’expérience reconnu** dans les listes et fiches,
avec un filtre 0–2 ans, >2 ans ou minimum non reconnu. Il permet notamment de
repérer les six offres prioritaires actives demandant trois ans. « Non reconnu »
ne signifie pas zéro expérience ; les scores restent inchangés. Voir le
[bilan du lot 35](docs/VALIDATION-LOT35.md).

Le lot 34 retire deux présentations générales DRW du calcul des actifs et termes
de profil. **Neuf scores sont corrigés**, dont Floor Trader **94 → 82**, avec son
indice junior conservé à 20/20. Les descriptions complètes restent disponibles.
Voir l'[audit des preuves](docs/DRW-EVIDENCE-AUDIT-LOT34.md) et le
[bilan du lot 34](docs/VALIDATION-LOT34.md).

Le lot 33 reconnaît l'indice junior de **DRW Floor Trader** à partir des preuves
Campus, temps plein et diplôme attendu : score corrigé de **79 à 94**. Les stages
et exigences d'expérience restent contrôlés ; la date de dernière collecte est
préservée. Voir l'[audit](docs/DRW-CAMPUS-AUDIT-LOT33.md) et le
[bilan du lot 33](docs/VALIDATION-LOT33.md).

Le lot 32 actualise IMC, DRW, Flow Traders, Jump et XTX : **89 offres relues et une
nouvelle offre DRW Floor Trader**, Chicago, début été 2027, score initial 79.
La base contient désormais 814 offres. L'aperçu précise les champs modifiés ;
l'[audit qualité](docs/GREENHOUSE-QUALITY-LOT32.md) documente les limites du score.
Voir le [bilan du lot 32](docs/VALIDATION-LOT32.md).

Le lot 31 ajoute `trading-radar scan --dry-run --source flow_traders` :
[aperçu de collecte](docs/SCAN-PREVIEW.md) sur une copie temporaire vérifiée,
sans importer les changements ni envoyer d'alertes. `--demo` permet de l'essayer
hors réseau. Voir le [bilan du lot 31](docs/VALIDATION-LOT31.md).

Le lot 29 distingue la préférence `Experience Desirable:` des exigences et
reconnaît les années d'expérience explicitement ajoutées au diplôme. Les
[alternatives ambiguës](docs/DEGREE-EXPERIENCE-LOT29.md) sont écartées de cette
nouvelle extraction. Le recalcul des scores fonctionne sans initialiser Telegram.

Le lot 28 ajoute `trading-radar backup plan data/backups --json` : inventaire vérifié
et [plan de conservation](docs/BACKUP-RETENTION.md) des sauvegardes, avec motifs et
volume des candidats au retrait. La commande ne supprime aucun fichier.

Le lot 26 affine les exigences d'expérience : les préférences directement attachées, notamment `ideally`, ne sont plus traitées comme des minima obligatoires. La commande `trading-radar rescore --dry-run` permet de [prévisualiser les changements de score](docs/SCORING-AUDIT.md) sans écrire dans la base. Voir l'[audit du corpus](docs/EXPERIENCE-SCOPE-AUDIT-LOT26.md).

Le lot 25 ajoute [l'édition locale des candidatures](docs/DASHBOARD-EDITING.md) : formulaire dans la fiche d'une offre, historique avant/après et protection contre les modifications concurrentes. Démarrer avec `trading-radar dashboard serve --edit-applications`. Les exports HTML et le serveur sans cette option restent en lecture seule.

Le lot 24 ajoute les [statistiques historiques](docs/TRENDS.md) : onglet **Tendances** sur 7, 30 ou 90 jours et commande `trading-radar trends --days 30`. Premières détections, modifications des fiches et résultats des scans sont comptés séparément, en lecture seule. Trois sous-agents ont réalisé les calculs, la commande et l'interface. Voir le [bilan du lot 24](docs/VALIDATION-LOT24.md).

Depuis la racine du projet, l'environnement `.venv` est déjà installé :

```powershell
.\.venv\Scripts\python.exe -m trading_radar doctor
.\.venv\Scripts\python.exe -m trading_radar list --min-score 70
.\.venv\Scripts\python.exe -m trading_radar scan --company "Jane Street"
.\.venv\Scripts\python.exe -m trading_radar watch
```

`watch` reste au premier plan jusqu'à Ctrl+C. Il n'est pas lancé automatiquement. Les alertes sont désactivées par défaut. Le premier scan de **chaque source** constitue une référence silencieuse, y compris lorsqu'on ajoute un employeur après plusieurs jours d'utilisation.

## Installation sur un autre poste

Python 3.12 recommandé pour les dépendances optionnelles ; le cœur accepte Python 3.11+. Installation depuis ce dépôt, puis exécution depuis sa racine (les configurations et fixtures sont des fichiers du dépôt).

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell : .\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
```

Pour reproduire les versions validées, préférer le parcours [uv verrouillé](docs/DEPENDENCIES.md), avec uv 0.11.8 :

```bash
uv sync --locked --extra dev
uv run --no-sync trading-radar --help
```

L'installation pip ci-dessus respecte les plages de compatibilité mais n'utilise pas `uv.lock`.

Extensions facultatives :

```bash
python -m pip install -e '.[ats,jobspy]'
```

Le paquet `python-jobspy` impose certaines anciennes dépendances natives. Privilégier Python 3.12 si l'installation échoue avec une version plus récente. Le cœur et ses connecteurs directs n'en dépendent pas.

## Démonstration hors ligne

```bash
trading-radar scan --demo
trading-radar list --demo --min-score 85
trading-radar stats --demo
trading-radar scan --demo
```

Les huit offres sont **synthétiques**, avec des liens `example.com`. Elles vont dans `data/demo.db` et `data/demo.csv`, séparément des données réelles. Premier passage : huit nouvelles offres, dont cinq pertinentes. Second passage : zéro nouvelle offre et zéro notification. Aucun message Telegram n'est envoyé par ce mode.

## Commandes

```bash
trading-radar scan
trading-radar scan --company "Jane Street"
trading-radar scan --source greenhouse
trading-radar scan --source workday
trading-radar scan --source goldman
trading-radar scan --source goldman_campus
trading-radar scan --source bnp_paribas
trading-radar scan --source ubs
trading-radar scan --source ubs_professionals
trading-radar scan --source societe_generale
trading-radar scan --source credit_agricole_cib
trading-radar scan --source hsbc_graduates
trading-radar scan --source hsbc_professionals
trading-radar scan --source macquarie
trading-radar scan --source nomura_campus
trading-radar scan --source nomura_professionals
trading-radar scan --source optiver
trading-radar scan --source imc
trading-radar scan --source drw
trading-radar scan --source sig
trading-radar scan --source flow_traders
trading-radar scan --source jump_trading
trading-radar scan --source xtx_markets
trading-radar scan --company "Citi"
trading-radar watch
trading-radar list --min-score 85
trading-radar list --new
trading-radar explain JOB_ID
trading-radar export --output data/jobs.csv
trading-radar rescore
trading-radar stats
trading-radar trends --days 30
trading-radar rescore --dry-run
trading-radar applications list --status "To Apply"
trading-radar applications show JOB_ID
trading-radar applications update JOB_ID --status "Reviewing" --notes "Relire les exigences"
trading-radar applications history JOB_ID
trading-radar deadlines list --days 30
trading-radar deadlines reminders
trading-radar alerts list
trading-radar alerts list --status pending
trading-radar alerts show ALERT_ID
trading-radar alerts history ALERT_ID
trading-radar audit
trading-radar audit --max-age-hours 48 --output data/freshness.json
trading-radar doctor
trading-radar doctor --network
```

`--config-dir` permet d'utiliser un autre dossier de configuration. `list --new` sélectionne les offres observées pour la première fois lors du dernier passage sur leur source ; ce n'est pas une boîte de réception avec acquittement. `list` conserve aussi les offres fermées et indique `active`. `explain` expose chaque composante et les motifs d'exclusion.

`--source` accepte le type de connecteur (`workday`, `goldman`) ou la clé de configuration (`goldman_campus`, `bnp_paribas`). Le premier sélectionne toutes les sources de ce type ; la seconde permet un scan ciblé.

`doctor --network` interroge les sources activées sans importer leurs offres ni envoyer de message. Les scans utilisent le code retour 1 en cas de source en échec et 2 si aucun collecteur ne correspond aux filtres. Les erreurs d'une source ne bloquent pas les autres.

`audit` lit SQLite hors réseau, en lecture seule et dans un instantané cohérent. Il ne crée pas de base absente et n'initialise pas Telegram. Seuil par défaut : 24 heures. États : `fresh` (dernier succès assez récent), `stale`, `failed` (échec plus récent que le succès), `never_scanned`, `unknown` (date invalide ou future) et `disabled`. Les compteurs de fiches dédupliquent les observations par source et distinguent celles revues récemment de celles non revérifiées. Une fiche ancienne n'est pas déclarée fermée. L'intervalle configuré ne prouve pas qu'un watcher fonctionne ; l'audit reste informatif et retourne 0 même en présence de sources anciennes ou en échec.

## Sources disponibles

| Connecteur | Fonctionnement | État initial |
|---|---|---|
| Greenhouse | API Job Board publique, descriptions incluses | Jane Street activé et testé en réseau |
| Workday | Recherche CXS publique paginée et descriptions détaillées | Deutsche Bank, Morgan Stanley, Citi et Barclays activés |
| Goldman | Recherche GraphQL anonyme et fiches publiques HTML | Sources professional/early career et campus activées séparément |
| BNP Paribas | Formulaire public GET, pagination HTML, descriptions JobPosting | Recherche Trading sur le portail français, offres internationales |
| UBS | Tableaux BrassRing publics, session anonyme et fiches détaillées | Étudiants/graduates et professionnels activés séparément |
| Société Générale | Répertoires FR/EN et fiches publiques HTML/JobPosting | Activé, références bilingues réunies avant import |
| Crédit Agricole CIB | Catalogue Talentsoft public et fiches détaillées | Activé, filtrage Trading/Markets après pagination |
| HSBC | Catalogue campus SuccessFactors et recherche professionnelle Eightfold | Étudiants/graduates et professionnels activés séparément |
| Macquarie | Recherche Avature et fiches publiques | Activé, recherche Trading et filtre de titres |
| Nomura | Tableau campus Oleeo et recherche professionnelle SuccessFactors | Campus et professionnels activés séparément |
| Optiver | API publique du site, pagination et fiches HTML/JobPosting | Activé, titres filtrés ; événements et viviers hors priorité |
| Greenhouse filtré | Tableaux publics IMC, DRW, Flow Traders, Jump et XTX, descriptions et métadonnées | Activés, périmètre Trading/Markets ; aucune fermeture par absence |
| SIG / Susquehanna | Catalogue iCIMS/Jibe public paginé | Activé, Trading/Markets ; découverte, Operations et Sports Analytics écartés |
| Citadel Securities | Portail officiel repéré | Désactivé après HTTP 403 ; connecteur non implémenté |
| Oracle | Recherche Candidate Experience et détails publics | Tests hors réseau ; JPMorgan désactivé, HTTP 403 |
| Lever | API Postings publique, pagination, région globale ou EU | Testé sur fixture ; ajouter un tenant |
| Ashby | API Job Postings publique | Testé sur fixture ; ajouter un tenant |
| `ats_dataset` | Recherche dans le jeu de données public `ats-scrapers` | Optionnel, désactivé |
| `jobspy` | Indeed, Google, Glassdoor, ZipRecruiter | Optionnel, désactivé, contrat testé avec simulation |

L'adaptateur `ats_dataset` lit un dataset publié ; il **ne surveille pas directement** toutes les banques via leurs ATS. Sa fraîcheur dépend de son fournisseur. Les intégrations SuccessFactors et iCIMS sont propres aux portails vérifiés ci-dessus ; SmartRecruiters et Taleo restent à intégrer. Oracle nécessite encore une validation réseau réussie. LinkedIn est désactivé dans l'adaptateur actuel. Les connecteurs natifs fonctionnent sans `ats-scrapers`.

### Ajouter une société

Dans `config/companies.yaml`, ajouter une entrée avec un identifiant stable :

```yaml
companies:
  identifiant_stable:
    name: Nom de la société
    enabled: true
    ats: greenhouse  # greenhouse, lever ou ashby
    tenant: slug_public_verifie
    career_url: https://example.com/careers
    country: global  # EU sélectionne api.eu.lever.co pour Lever
    scan_interval: 300
    request_interval: 2
    notes: Indiquer comment le tenant a été vérifié.
```

Le slug doit provenir de la page carrière officielle. Vérifier avec `doctor --network` avant utilisation. Ne pas renommer arbitrairement les identifiants de source : ils servent à l'historique et au démarrage silencieux. Ne mettre aucun secret dans les fichiers YAML. Aucun en-tête arbitraire ni proxy n'est accepté dans ce premier lot.

Pour Workday, utiliser `ats: workday` et la racine du portail public comme `career_url`. Voir les exemples activés dans `config/companies.yaml` et les options dans [SOURCES.md](docs/SOURCES.md).

### Ajouter un collecteur

Implémenter `Collector.collect() -> Collection` dans un nouveau module, puis l'enregistrer dans `build_collector`. Utiliser le client HTTP partagé pour les collectes directes et retourner des `RawJob`. Ajouter une fixture et un test d'intégration. Le champ `complete=True` est réservé à un inventaire exhaustif ayant terminé toutes ses pages. Une recherche filtrée ou tronquée doit retourner `False` pour empêcher les fausses fermetures.

## Configuration et Telegram

Copier `.env.example` vers `.env` :

```powershell
Copy-Item .env.example .env
```

1. Créer un bot via [BotFather](https://t.me/BotFather), puis démarrer une conversation avec ce bot.
2. Enregistrer son token dans `TELEGRAM_BOT_TOKEN` et le chat destinataire dans `TELEGRAM_CHAT_ID`. L'identifiant du chat peut être obtenu via la méthode [getUpdates de Telegram](https://core.telegram.org/bots/api#getupdates), après avoir envoyé un message au bot. Ne pas coller le token dans le terminal, une capture ou le dépôt.
3. Mettre `ALERTS_ENABLED=true` lorsque les envois sont souhaités.
4. Vérifier `trading-radar doctor`, puis lancer `watch`.

Sans ces paramètres, le scanner, le classement et le CSV fonctionnent. Activer les alertes ne crée pas de notification rétroactive pour toutes les offres précédemment observées. Seules les nouvelles offres à partir du seuil configuré (70 par défaut), les réouvertures et les modifications significatives de titre, lieu ou deadline sont notifiées. Les changements de description sont historisés sans notification.

Les messages affichent le score, ses six composantes, les raisons, la date de première observation, les dates connues et le lien de candidature. Les dates absentes restent inconnues : `updated_at` Greenhouse n'est pas présenté comme une date de publication.

Les alertes utilisent une file persistante. Une réponse de rejet peut être retentée. Après une interruption dont l'issue est incertaine, l'alerte passe à `unknown` (ou reste `sending` après un crash) et n'est pas renvoyée automatiquement. Telegram ne fournit pas de clé d'idempotence pour cet envoi : cette décision privilégie l'absence de doublons, au prix d'un possible message perdu. `stats` affiche ces états pour vérification manuelle.

## Score et qualité

| Composante | Maximum |
|---|---:|
| Pertinence Trading | 30 |
| Compatibilité junior | 20 |
| Date de début | 15 |
| Front Office | 15 |
| Classe d'actifs | 10 |
| Adéquation au profil | 10 |

Score 85–100 : URGENT ; 70–84 : HIGH ; 55–69 : MEDIUM ; inférieur à 55 : LOW. Les exclusions ramènent le total à zéro tout en conservant les éléments d'explication. Le score repose sur les titres et des règles déterministes, avec un poids limité des descriptions. Répéter un mot-clé ne rapporte pas davantage. La réputation de l'entreprise et la géographie n'augmentent pas le score /100.

Une date de début inconnue vaut 7/15 ; un titre explicitement junior vaut 20/20. Les exigences d'expérience détectées diminuent la composante junior et peuvent exclure un poste. Les offres ambiguës nécessitent encore une lecture humaine. Les variantes géographiques sont normalisées et classées par niveau de préférence ; une offre multi-villes conserve ses différentes villes.

Les intitulés de stage, Summer Analyst/Associate et apprentissage sont exclus de la priorité full-time. VIE et graduate programmes à temps plein restent admissibles. Une contradiction entre année du titre et début annoncé dans la description est signalée et reçoit une note de date prudente. Après modification des règles, `rescore` actualise les offres déjà stockées et le CSV hors réseau, sans changer les dates d'observation ni envoyer de message.

L'urgence est séparée du score d'adéquation : bonus de récence +5/+3/+1 et bonus de deadline +5/+3/+1. Ce bonus n'altère jamais le /100. Les timestamps des offres et de l'historique sont conservés en UTC. Les dates saisies dans le suivi de candidature sont des jours calendaires, sans heure ni conversion de fuseau.

## Stockage et fiabilité

- SQLite en WAL, transactions par source, clés étrangères et index. Accès centralisé dans `Repository` pour permettre un futur backend PostgreSQL.
- Tables : `jobs`, `job_sources`, `job_versions`, `companies` (état des sources), `scan_runs`, `alerts`, `alert_history`, `applications`, `application_history`, `score_history`, `schema_version`.
- Identité prioritaire : source + entreprise + ID externe, puis URL canonique, puis entreprise + titre + lieu exacts lorsqu'une seule correspondance existe sur une autre source.
- Deux IDs différents sur la même source restent distincts, même avec une URL générique commune. Les fragments d'URL qui peuvent identifier un poste sont conservés. Les rapprochements incertains ne sont pas fusionnés automatiquement ; la recherche floue reste à ajouter.
- La source officielle prime sur l'agrégateur. Les versions et les premières observations sont conservées.
- Une offre n'est fermée qu'après deux absences dans des inventaires complets et si aucune autre source ne la voit encore active. Un résultat soudainement entièrement vide déclenche une erreur et exige une vérification, sans fermeture massive.
- Timeouts, reprises exponentielles avec jitter, prise en compte de `Retry-After`, rythme par hôte et concurrence limitée. Le watcher espace davantage les tentatives après des erreurs.
- Les collectes directes consultent `robots.txt`. Les réponses interdites, redirections non gérées et challenges ne sont pas contournés.
- Les bibliothèques optionnelles exécutent leur propre transport dans un sous-processus limité à 90 secondes. Leur nombre de requêtes internes et leur régulation ne sont pas mesurés par notre client HTTP ; elles restent désactivées par défaut.
- Un verrou interdit deux scanners simultanés sur le même fichier SQLite. Utiliser une seule instance du watcher par base.
- Les données brutes sont désactivées par défaut. Les logs structurés ne contiennent ni token Telegram ni texte brut des exceptions HTTP externes.

Sauvegarde et exercice de récupération, avec des chemins nouveaux à chaque exécution :

```bash
trading-radar backup create data/backups/radar-2026-09-17.zip
trading-radar backup verify data/backups/radar-2026-09-17.zip
trading-radar backup plan data/backups --json
trading-radar backup restore data/backups/radar-2026-09-17.zip data/restore-check/jobs.db
```

La restauration ne sélectionne pas la nouvelle base. Le [guide de récupération](docs/BACKUPS.md) précise les contrôles avant reprise, notamment les alertes déjà livrées depuis la sauvegarde, et les limites de conservation locale.

`applications list/show/update/history` permet désormais de gérer le suivi local. Les modifications sont validées, verrouillées et historisées dans une transaction ; les scans préservent les champs saisis. Le CSV ajoute `job_id`, `application_date`, `recruiter`, `notes`, `next_action` et `next_action_date` à ses colonnes existantes. Les douze statuts et les commandes sont décrits dans [APPLICATIONS.md](docs/APPLICATIONS.md). Les rappels de deadline disposent d'une [prévisualisation et d'une activation distincte](docs/DEADLINES.md) ; le dashboard permet leur consultation en lecture seule. Aucune candidature n'est envoyée par le radar.

## Docker / VPS

Le [guide d'exploitation](docs/OPERATIONS.md) couvre les contrôles préalables, la santé, les sauvegardes et la reprise. Créer `.env` depuis `.env.example` s'il n'existe pas, puis :

```bash
docker compose config --quiet
docker compose build
docker compose run --rm radar doctor
docker compose up -d
docker compose logs -f radar
docker compose exec radar trading-radar health
docker compose down
```

L'image utilise Python 3.12 et uv fixés par empreinte, les dépendances de `uv.lock`, un utilisateur non-root et un volume nommé `radar-data`. Compose garde la racine et les réglages YAML en lecture seule, fournit `/tmp` et limite les logs. L'image installe les connecteurs natifs. Utiliser les [sauvegardes SQLite](docs/BACKUPS.md), puis conserver une copie vérifiée hors du volume ; ne pas exécuter `down -v` si les données doivent être conservées. **Build et reprise Docker Linux validés en CI au lot 36**. Docker Desktop est installé localement, mais WSL reste à activer ; le contrôle du poste Windows et d’un éventuel VPS reste à effectuer.

`trading-radar health` fournit un JSON local et un code de sortie pour la supervision, sans créer ni migrer la base. Il mesure la fraîcheur des sources et signale les alertes incertaines. Un déploiement neuf reste critique jusqu'aux premières collectes réussies. Voir [HEALTH.md](docs/HEALTH.md).

Pour conserver explicitement une observation et comparer les deux dernières :

```bash
trading-radar monitor record
trading-radar monitor history --limit 10
trading-radar monitor show IDENTIFIANT
```

Les [rapports de santé](docs/MONITORING.md) vont dans `data/health-history`, sans modification de la base métier ni planification automatique. Le [cache conditionnel Workday](docs/WORKDAY-CACHE.md) est disponible pour le watcher et reste désactivé dans la configuration fournie.

## Dashboard local

Le lot 23 actualise Jump et corrige la lecture des intervalles d'expérience : `2–5+ ans` ne signifie plus un minimum de cinq ans. La base compte désormais 813 offres, dont 811 actives. Une mesure sur les quatre sources Workday ne montre aucune réutilisation possible du cache, qui reste désactivé. Voir le [bilan du lot 23](docs/VALIDATION-LOT23.md).

Le lot 22 ajoute un [dashboard en lecture seule](docs/DASHBOARD.md) : recherche et classement des offres, détail des scores, consultation des candidatures et santé des sources avec historique. L'export HTML autonome fonctionne hors ligne ; les données constituent un instantané à régénérer après une collecte ou une modification du suivi.

```bash
trading-radar dashboard export data/dashboard/index.html
trading-radar dashboard serve --port 8765
trading-radar dashboard serve --edit-applications --port 8765
```

Le serveur d'aperçu écoute sur `http://127.0.0.1:8765` uniquement. Relancer la commande pour actualiser sa vue. L'export inclut les notes du suivi et doit rester privé. Utiliser `--overwrite` pour remplacer explicitement un export existant.

## Architecture

```text
.
├── docs/                     master prompt, suivi des tâches, validation
├── config/                   settings.yaml, companies.yaml, keywords.yaml
├── src/trading_radar/
│   ├── cli.py                scan, watch, list, explain, export, stats, doctor
│   ├── config.py             validation YAML et environnement
│   ├── models.py             RawJob, Job, Score, métriques
│   ├── collectors.py         interface et connecteurs publics
│   ├── workday.py            recherche CXS, pagination, détails, limites
│   ├── vendor.py             frontière avec les bibliothèques optionnelles
│   ├── http.py               transport HTTP partagé
│   ├── normalizer.py         textes, entreprises, lieux, dates, URLs
│   ├── scoring.py            classification, exclusions, score
│   ├── storage.py            transactions, déduplication, historique
│   ├── backups.py            snapshot WAL, archive vérifiée, restauration
│   ├── backup_retention.py   inventaire et plan de conservation sans suppression
│   ├── health.py             contrôle local de santé et fraîcheur
│   ├── monitoring.py         archives et comparaison des rapports de santé
│   ├── trends.py             statistiques quotidiennes UTC en lecture seule
│   ├── score_audit.py        aperçu des recalculs sans écriture
│   ├── trends_cli.py         commande trends et sortie JSON
│   ├── dashboard_data.py     instantané SQLite en lecture seule
│   ├── dashboard.py          export HTML et serveur local
│   ├── dashboard_editor.py   serveur local avec édition explicite du suivi
│   ├── dashboard_applications.py suivi transactionnel et contrôle des conflits
│   ├── dashboard_assets/     interface autonome, styles et interactions
│   ├── http_cache.py         cache mémoire pour revalidation conditionnelle
│   ├── scanner.py            orchestration, bootstrap, alertes, métriques
│   ├── notifications.py      Telegram
│   └── export.py             CSV atomique
├── tests/                    tests hors réseau et fixtures
├── data/                     bases et exports locaux ignorés par Git
├── .github/workflows/ci.yml
├── Dockerfile
└── docker-compose.yml
```

## Audit ciblé Workday

La [sonde Workday](docs/WORKDAY-QUERY-PROBE.md) prépare par défaut un plan hors réseau.
Avec `--network`, elle compare au maximum deux recherches aux chemins déjà connus,
lit les fiches supplémentaires dans un budget limité et conserve les preuves sans import.
Les [contrôles d'intégrité](docs/WORKDAY-INTEGRITY-LOT27.md) rejettent les fiches
incohérentes avant toute écriture du scan.

Le lot 30 ajoute `--facet KEY=VALUE` pour restreindre une mesure à des filtres
publics vérifiés sur le portail. L'[audit Citi](docs/CITI-FACET-SCOPE-LOT30.md)
couvre deux catégories et deux termes ; ses 26 offres retenues étaient déjà
connues. La configuration des scans reste inchangée.

## Vérifications

```bash
ruff check src tests
ruff format --check src tests
mypy src/trading_radar
pytest --cov=trading_radar --cov-report=term-missing
trading-radar scan --demo
```

La CI est configurée pour Python 3.11 à 3.14 avec le lock uv, puis pour un build et une restauration Docker sur un volume synthétique sans réseau. L'exercice vérifie aussi l'historisation de santé, l'export du dashboard et le plan de conservation des sauvegardes. Les tests utilisent des fixtures, des transports simulés et un serveur sur la boucle locale. Les résultats effectivement obtenus sont dans [la validation du lot 30](docs/VALIDATION-LOT30.md), avec l'historique des lots précédents dans `docs/`.

## Dépannage

- **Aucune source sélectionnée** : vérifier `enabled`, l'orthographe de `--company` et le type `--source`.
- **Source en erreur** : lancer `doctor --network`, consulter `stats`, puis vérifier la page carrière manuellement. Ne pas contourner un refus d'accès.
- **Bibliothèque absente** : installer l'extra correspondant dans le même environnement Python.
- **Base verrouillée** : arrêter la deuxième instance du watcher ; ne pas effacer la base.
- **Aucune alerte** : vérifier l'activation, le seuil et le bootstrap silencieux. Une offre déjà connue ne sera pas renotifiée sans changement significatif.
- **Résultat incorrect** : conserver un exemple anonymisé comme fixture, corriger les règles et ajouter un test avant d'élargir la couverture.
- **Changement de configuration** : redémarrer le watcher ; les fichiers sont chargés au démarrage.

## Références techniques

Les adaptateurs s'appuient sur les contrats publics : [Greenhouse Job Board](https://docs.greenhouse.io/job-board.html), [Lever Postings](https://github.com/lever/postings-api), [Ashby Job Postings](https://developers.ashbyhq.com/docs/public-job-posting-api), [JobSpy](https://github.com/speedyapply/JobSpy), [ats-scrapers](https://github.com/kalil0321/ats-scrapers), [Telegram sendMessage](https://core.telegram.org/bots/api#sendmessage).

Utiliser les sources publiques à un rythme raisonnable, respecter leurs restrictions et désactiver les collecteurs qui ne peuvent plus être interrogés normalement. Aucun mécanisme de contournement d'authentification ou de CAPTCHA n'est implémenté.
