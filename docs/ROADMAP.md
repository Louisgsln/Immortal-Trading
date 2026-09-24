# Suivi de construction

Référence : Master Prompt — Trading Job Radar.md, section 61. Ce document suit le périmètre demandé ; le master prompt original est conservé sans modification.

## Lot 1 — Pipeline vertical

| Tâches du master prompt | Résultat |
|---|---|
| 1–3 : inspection, structure, pyproject | Réalisé ; dépôt Git local initialisé |
| 4–6 : gitignore, environnement, YAML | Réalisé |
| 7–8 : modèles et SQLite | Réalisé ; historique et suivi de candidature préparés |
| 9–10 : collecteurs et ATS | Greenhouse, Lever, Ashby directs ; adaptateur dataset ats-scrapers |
| 11 : JobSpy | Adaptateur optionnel, isolé et testé par contrat ; sites à valider séparément |
| 12–14 : normalisation, exclusions, score | Réalisé, avec explications et contre-exemples |
| 15–16 : déduplication et bootstrap | Réalisé ; identité par entreprise/source, démarrage silencieux par source |
| 17–18 : CSV et Telegram | Réalisé ; Telegram testé avec transport simulé |
| 19–20 : CLI, logs, métriques | Réalisé ; commandes scan/watch/list/explain/export/stats/doctor |
| 21 : tests | Tests unitaires et d'intégration hors réseau |
| 22 : Docker | Fichiers fournis ; lancement Docker non vérifié sur ce poste |
| 23 : GitHub Actions | Workflow fourni ; pas de dépôt distant ni de run hébergé |
| 24 : README | Installation, architecture, configuration, exploitation et limites documentées |
| 25–28 : tests, lint, corrections, dry run | Vérifiés localement ; scan réel Jane Street également exécuté |

### Décisions du premier lot

- Le backend est construit avant le dashboard.
- Trois API publiques directes précèdent l'intégration des ATS bancaires complexes.
- `ats-scrapers` est utilisé via son dataset public ; ses collecteurs directs ne sont pas exécutés dans cette version. Cela ne remplace pas la surveillance directe Workday/SuccessFactors demandée pour la suite.
- Les packages optionnels ne bloquent pas le cœur. Pas de clé LLM nécessaire.
- Déduplication prudente : les fusions floues automatiques sont reportées jusqu'à disposer d'un corpus de validation.
- SQLite natif, sans ORM, derrière un dépôt centralisé. Un changement vers PostgreSQL nécessitera une implémentation du dépôt et une migration des données.
- Le scan initial réel est une référence silencieuse. Telegram et la surveillance continue restent à activer dans la configuration d'exploitation.

## Lot 2 — Premières banques officielles

- Connecteur Workday natif ajouté au transport HTTP commun : recherche POST publique, pagination, détails et lieux multiples.
- Deutsche Bank, Morgan Stanley, Citi et Barclays configurés sur des portails publics vérifiés. Détails du périmètre dans [SOURCES.md](SOURCES.md).
- Protections testées : total absent sur les pages suivantes, limite 2 000, pages courtes/répétées, détails manquants, chemins invalides et budget de durée.
- Recherches partielles explicitement marquées comme telles ; aucune fermeture déduite de leur seule disparition.
- Stages et Summer Analyst/Associate exclus du classement prioritaire ; VIE conservés. Contradictions de dates signalées.
- Commande `rescore` pour appliquer les règles aux offres locales sans nouvelle collecte ni fausse observation.
- Goldman Sachs et JPMorgan identifiés : connecteurs respectivement à analyser et Oracle à implémenter. Ils ne sont pas présentés comme actifs.

## Lot 3 — Goldman Sachs et préparation Oracle

- Recherche anonyme Goldman vérifiée à partir du contrat utilisé par son site public : pagination de 20 résultats, union des requêtes, filtres de titres et descriptions complètes issues des fiches HTML.
- Couverture des catégories `EARLY_CAREER` et `PROFESSIONAL` ; les programmes campus restent à intégrer séparément. Les avis réglementaires « Notice of Filing » ne sont pas des offres retenues.
- Connecteur Oracle Candidate Experience implémenté avec pagination dans le finder et lecture des descriptions, responsabilités et qualifications.
- JPMorgan reste désactivé : HTTP 403 depuis cet environnement. Les tests synthétiques du connecteur ne remplacent pas la validation réseau.
- Limites de résultats, budget de durée, identifiants stables, erreurs GraphQL et réponses incomplètes testés. Toutes ces recherches restent partielles, sans fermeture déduite d'une absence.
- `doctor` expose les sources désactivées avec leurs notes.

## Lot 4 — Campus Goldman et BNP Paribas

- Source campus Goldman distincte, avec recherches `trading` et `ficc`, descriptions complètes et démarrage silencieux propre à la source.
- Connecteur BNP Paribas natif : formulaire GET public, contrôle du mot-clé et de toutes les pages, fiches JobPosting et lieux multiples.
- Recherches toujours partielles, sans fermeture par absence. Dates campus non confondues avec le début d'emploi.
- Exclusions complétées pour les variantes `OffCycle` et `Stage` rencontrées dans le nouveau périmètre.
- Filtre CLI `--source` utilisable par type de connecteur ou clé de source.
- Portails UBS et Société Générale découverts ; configuration désactivée en attendant leurs connecteurs et validation réseau.
- Bilan des imports et contrôles dans [VALIDATION-LOT4.md](VALIDATION-LOT4.md).

## Lot 5 — UBS étudiants/graduates

- Connecteur du tableau public UBS, avec bootstrap de session anonyme, pagination contrôlée et détails complets.
- Lecture de toutes les pages du tableau puis filtrage Trading/Markets local ; pas de filtre serveur supposé efficace.
- Paramètres de langue des liens publics validés ; données de session exclues du stockage métier.
- 17 offres importées au premier passage silencieux. Portail UBS professionnel hors périmètre.
- Alias BNP stabilisés avant import, avec rejet des conflits de contenu sur un même identifiant.
- Résultats dans [VALIDATION-LOT5.md](VALIDATION-LOT5.md).

## Lot 6 — Société Générale

- Lecture directe des deux répertoires publics, sans utiliser le moteur Quantum ni OAuth.
- Contrôle des comptes annoncés, références, URLs et langues ; anglais choisi de manière stable pour les références communes.
- Fiches détaillées : titre visible, missions et profil requis complets, publication contrôlée contre la date affichée, début d'emploi extrait uniquement de son libellé explicite.
- `validThrough` non converti en deadline : valeur incohérente avec la sémantique visible sur les fiches inspectées.
- « V.I.E. » reconnu comme « VIE » et « structuration » comme « structuring » dans le score.
- Titres « application support » exclus du classement prioritaire après vérification d'un faux positif réel.
- 33 offres importées au premier passage silencieux. Bilan dans [VALIDATION-LOT6.md](VALIDATION-LOT6.md).

## Lot 7 — Crédit Agricole CIB et HSBC

- Crédit Agricole CIB : catalogue public paginé, titres filtrés localement, descriptions et critères candidat complets, contrat et expérience minimale structurée.
- HSBC : catalogue étudiants/graduates, pagination publique contrôlée, fiches SuccessFactors, lieux multiples, dates de début et deadlines UTC explicites.
- Classement : exclusion des contrats de stage même sans mention dans le titre ; expérience minimale structurée prioritaire sur un intitulé junior.
- Historique des changements de contrat et d'expérience minimale ; anciens payloads SQLite compatibles avec le nouveau champ facultatif.
- Parseur HTML partagé avec Société Générale, sans dépendance supplémentaire.
- Résultats dans [VALIDATION-LOT7.md](VALIDATION-LOT7.md).

## Lot 8 — Macquarie et Nomura campus

- Macquarie : recherche Avature publique, pagination de neuf cartes, conservation du filtre, fiches détaillées et critères requis.
- Nomura : tableau campus Oleeo, références contrôlées, routes publiques stables et description intégrale ; événements et portail professionnel distinct hors périmètre.
- Niveau junior/senior explicite intégré au score ; tranches d'expérience Macquarie lues dans la rubrique candidat. Les stages campus restent exclus de la priorité.
- Résultats et contrôles dans [VALIDATION-LOT8.md](VALIDATION-LOT8.md).

## Lot 9 — Optiver et vérification Citadel Securities

- Optiver : API publique du site, pagination de 16 cartes, contrôle du total et des doublons, puis vérification des fiches HTML et JobPosting.
- Niveaux Graduate/Early Careers exploités ; stages exclus même sans mention dans le titre. Programmes Career Kickstarter et Expressions of Interest conservés avec score nul ; événement The Trading Floor hors collecte.
- Citadel Securities : portail identifié, refus HTTP 403 constaté. Source désactivée, aucun connecteur annoncé comme opérationnel.
- Résultats et contrôles dans [VALIDATION-LOT9.md](VALIDATION-LOT9.md).

## Lot 10 — IMC et DRW

- Deux tableaux Greenhouse publics reliés aux fiches officielles ; contrôle du total, des identifiants, de l'employeur, des URLs et des descriptions avant import.
- IMC : flux global, niveaux Graduate/Intern, exclusion des prospect posts et annonces marquées cachées, débuts d'emploi explicites.
- DRW : tableau anglais, contrats, publication et saison cible de prise de poste. Tableau français distinct hors périmètre.
- 26 fiches importées pour chaque employeur ; deuxième passage stable. Quatre postes juniors indiquent explicitement une prise de poste en 2027.
- Bilan dans [VALIDATION-LOT10.md](VALIDATION-LOT10.md).

## Lot 11 — SIG / Susquehanna et Flow Traders

- SIG : catalogue public iCIMS/Jibe paginé, descriptions et exigences intégrales, contrôle du catalogue et des identifiants.
- Catégories de découverte, Operations et Sports Analytics exclues du périmètre. Les contrats INTERN contradictoires avec New Graduates restent exclus de la priorité.
- Flow Traders : extension du connecteur Greenhouse, catégorie Events exclue et dates de début publiées conservées, même anciennes ou absentes.
- 49 fiches SIG et 10 Flow Traders importées ; bilan dans [VALIDATION-LOT11.md](VALIDATION-LOT11.md).

## Lot 12 — Jump Trading et XTX Markets

- Tableaux Greenhouse reliés aux pages officielles, vérifiés en direct ; identifiants du tableau XTX comparés au miroir JSON utilisé par son site.
- Jump Trading : URLs personnalisées contrôlées, contrats Campus/Experienced/Intern conservés. Aucune année d'entrée déduite du libellé Campus.
- XTX : classification Trading Tech appuyée à la fois par le département et les missions du poste ; l'infrastructure ML du même département ne reçoit pas cette classification.
- Champ de rôle facultatif, compatible avec les anciens payloads et historisé. Le recalcul des 722 anciennes fiches ne change aucun score.
- 23 fiches Jump et une XTX importées ; second passage stable. Bilan dans [VALIDATION-LOT12.md](VALIDATION-LOT12.md).

## Lot 13 — UBS et HSBC professionnels

- UBS : extension du connecteur aux paramètres vérifiés du tableau professionnel ; contexte de session séparé, pagination complète, descriptions et exigences conservées.
- HSBC : recherche Eightfold publique, pages de dix, contrôle des totaux et relecture de la première page ; concordance des identifiants, titres, lieux et fiches JobPosting. La division Wealth & Premier Banking est hors périmètre.
- Lecture robots corrigée avec Protego : règles Allow/Disallow les plus précises, jokers, groupes d'agent et Crawl-delay. Aucun changement des refus HTTP ou du mode de repli fermé si la politique est indisponible.
- Exclusions de titre pour Legal, COO et Business Manager, validées contre les nouveaux faux positifs UBS. Les portails professionnels n'impliquent pas automatiquement une séniorité élevée ni une date de début.
- Imports et vérifications dans [VALIDATION-LOT13.md](VALIDATION-LOT13.md).

## Lot 14 — Nomura professionnels

- Recherche SuccessFactors publique, pages de 100, contrôle des totaux et relecture de la première page ; les doublons d'affichage mobile/ordinateur sont réunis par référence.
- Filtre de titres Trading/Markets étendu à eTrading ; division Operations écartée. Les mêmes intitulés GM-Global Markets gardent leurs références distinctes.
- Fiches JobPosting, descriptions complètes, publication UTC, contrôle de l'employeur et de l'identité de candidature sans ouverture du formulaire.
- Grade Corporate Title, minimum d'expérience et contrat à durée déterminée explicitement publié. Les grades seniors priment sur un titre d'annonce ambigu ; aucune date d'entrée n'est supposée.
- Lead Support Analyst exclu de la priorité après lecture d'un rôle réel de support informatique. Les Trading Support quantitatifs ou de financement restent évalués sur leurs preuves propres.
- Résultats et contrôles dans [VALIDATION-LOT14.md](VALIDATION-LOT14.md).

## Lot 15 — Fraîcheur et couverture Workday

- Commande `audit` hors réseau : lecture seule, seuil configurable, états des sources et observations des fiches distingués, export JSON facultatif.
- Comparaison de cinq recherches sur trois banques ; Citi partiellement audité, Structuring dépassant le budget. Aucun supplément pertinent démontré selon le score actuel : requête Trading conservée.
- Actualisation des quatre banques Workday : douze nouvelles fiches, trois modifications. Les fiches absentes restent conservées sans fermeture implicite.
- Faux positif senior Desk Head corrigé après lecture de sa description ; contrôles de cohérence des titres entre requêtes renforcés.
- Résultats et limites dans [VALIDATION-LOT15.md](VALIDATION-LOT15.md).

## Lot 16 — Suivi des candidatures et actualisation restante

- Commandes `applications list/show/update/history` : douze statuts, édition partielle, dates calendaires strictes, recruteur, notes et prochaines actions.
- Historique avant/après atomique, verrou partagé avec les scans, saisies préservées lors des changements et réouvertures des offres. Migration additive SQLite 2 → 3.
- CSV enrichi avec l'identifiant stable et les champs de candidature ; protection des cellules contre les formules.
- Goldman professionnels, Goldman campus et Jane Street actualisés ; les 24 sources activées sont récentes au seuil de 24 heures au moment du bilan.
- Faux positifs du département Risk / Credit Risk de Goldman corrigés, avec contre-exemples de trading crédit.
- Mode d'emploi dans [APPLICATIONS.md](APPLICATIONS.md), résultats dans [VALIDATION-LOT16.md](VALIDATION-LOT16.md).

## Lot 17 — Deadlines et rappels conditionnels

- Consultation des échéances et prévisualisation des rappels hors réseau ; formats textuels explicites, preuves conservées et conflits bloquants.
- Dates sans heure/fuseau distinctes des instants ; aucune année déduite du programme, aucun UTC inventé pour une deadline naïve.
- Fenêtres J−7/J−3/J−1, statut et date de candidature contrôlés, fraîcheur maximale, déduplication et revalidation avant livraison.
- Activation distincte désactivée par défaut, bootstrap silencieux et démo préservés. Aucun watcher ni message réel lancé.
- Guide [DEADLINES.md](DEADLINES.md), mesures et tests dans [VALIDATION-LOT17.md](VALIDATION-LOT17.md).

## Lot 18 — Gestion des alertes incertaines

- Commandes locales `alerts list/show/history/resolve` ; décisions received/dismiss/retry avec motif et révision obligatoires.
- Historique des transitions système et opérateur, atomicité, verrou commun et refus des décisions périmées. Les reprises restent soumises aux contrôles de livraison.
- Accusés Telegram mal formés classés incertains, compteur de tentatives corrigé pour les nouveaux envois, migration additive SQLite 3 → 4.
- Base réelle vérifiée sans changement des données métier, file d'alertes vide, aucun envoi réel.
- Guide [ALERTS.md](ALERTS.md), bilan [VALIDATION-LOT18.md](VALIDATION-LOT18.md).

## Lot 19 — Sauvegardes SQLite et restauration vérifiée

- Commandes `backup create/verify/restore`, snapshots cohérents avec WAL, archive autonome et manifeste SHA-256.
- Contrôles d'intégrité, relations, schéma et comptes de lignes ; publication complète sans écrasement et récupération vers un nouveau fichier sous verrou.
- Protection des fichiers associés et des alias de verrou ; vérification sans migration ni initialisation de Telegram.
- Exercice réel : 811 fiches, 809 actives, contenu des 11 tables identique ; base en service préservée.
- Guide [BACKUPS.md](BACKUPS.md), preuves et limites dans [VALIDATION-LOT19.md](VALIDATION-LOT19.md).

## Lot 20 — Dépendances, santé et préparation Docker

- Trois sous-agents : verrouillage des dépendances, scénario de reprise et CI, contrôle de santé local ; intégration et revue croisée par l'agent principal.
- `uv.lock` réel, runtime/dev/extras résolus, contraintes de build ; installations isolées Windows Python 3.12 et 3.14.
- Commande `health` en lecture seule : intégrité, schéma, fraîcheur des sources et alertes incertaines, métriques dans une même transaction.
- Image à deux étapes, images Python/uv fixées par empreinte, utilisateur non-root, racine en lecture seule et logs bornés.
- CI préparée pour Python 3.11–3.14 puis build Docker et reprise sans réseau sur un volume synthétique. Parcours synthétique validé localement ; Docker/WSL absents, aucun build ou déploiement réel annoncé.
- Guides [DEPENDENCIES.md](DEPENDENCIES.md), [HEALTH.md](HEALTH.md), [OPERATIONS.md](OPERATIONS.md), bilan [VALIDATION-LOT20.md](VALIDATION-LOT20.md).

## Lot 21 — Historique de santé, cache Workday et couverture technique

- Trois sous-agents : archives de santé, cache conditionnel HTTP/Workday, audit des accès et de la couverture ; intégration et correction Jump par l'agent principal.
- `monitor record/history/show` : archives JSON séparées, publication sans écrasement, empreinte, filtres et comparaison des observations. Base métier préservée.
- Cache mémoire Workday optionnel et borné, partagé par le watcher ; clients et règles robots renouvelés entre scans. Revalidation obligatoire, aucun contenu périmé utilisé en secours.
- Audit historique Jump : 23 → 25 annonces retenues ; trois classifications techniques vérifiées, scores 51/53/53, aucun nouveau poste prioritaire ≥55. Contre-exemples support, stage et senior préservés.
- Citadel et JPMorgan restent bloqués dès robots.txt (HTTP 403), sans contournement. Aucune source activée ni collecte complète réelle dans ce lot.
- Guides [MONITORING.md](MONITORING.md), [WORKDAY-CACHE.md](WORKDAY-CACHE.md), audit [COVERAGE-AUDIT-LOT21.md](COVERAGE-AUDIT-LOT21.md), bilan [VALIDATION-LOT21.md](VALIDATION-LOT21.md).

## Lot 22 — Dashboard local en lecture seule

- Trois sous-agents : accès aux données, interface et validation indépendante. Intégration CLI, export, serveur et essais navigateur par l'agent principal.
- Export HTML autonome, sans dépendance supplémentaire : offres, filtres, recherche, tri, pagination, détail des scores et suivi des candidatures.
- Santé des 24 sources et dernières archives locales ; dates et précision des échéances conservées. Le fichier et le serveur présentent un instantané à régénérer.
- SQLite lu sans migration, offres et candidatures cohérentes dans une transaction. Protection de la base et des fichiers de référence, erreurs explicites et limite de 5 000 offres.
- Serveur sur 127.0.0.1 uniquement, sans API d'écriture ; données affichées comme texte, ressources embarquées et politique de sécurité du contenu.
- Export réel de 811 offres, dont 809 actives ; 11 tables et archives de santé préservées. Guide [DASHBOARD.md](DASHBOARD.md), bilan [VALIDATION-LOT22.md](VALIDATION-LOT22.md).

## Lot 23 — Actualisation Jump et exigences d'expérience

- Trois sous-agents : mesure Workday, audit d'expérience et capture Jump. Revue globale, sauvegarde, répétition puis import par l'agent principal.
- Catalogue public Jump relu : 108 annonces identiques au corpus conservé, 25 retenues. Deux identités ajoutées grâce aux règles du lot 21, quatre fiches mises à jour, aucune fermeture ni alerte.
- Intervalles d'expérience interprétés par leur borne inférieure, préférences attenantes distinguées ; preuve de track record Jump stockée dans le champ structuré existant. Audit des 811 offres avant modification et recalcul de sept fiches hors Jump.
- Mesure Workday : quatre fiches lues deux fois, aucun validateur ni réponse stockable, zéro réutilisation. Option de cache laissée désactivée.
- Base à 813 offres, 811 actives, 163 scores ≥70 et 250 ≥55 ; candidatures préservées, CSV et dashboard actualisés. 1 260 tests réussis.
- Rapports [EXPERIENCE-AUDIT-LOT23.md](EXPERIENCE-AUDIT-LOT23.md), [JUMP-REFRESH-LOT23.md](JUMP-REFRESH-LOT23.md), [WORKDAY-MEASURE-LOT23.md](WORKDAY-MEASURE-LOT23.md) et [VALIDATION-LOT23.md](VALIDATION-LOT23.md).

## Lot 24 — Statistiques historiques du radar

- Trois sous-agents : calculs SQLite, commande et documentation, interface Tendances ; intégration et validation par l'agent principal.
- Commande `trends --days 30` (1 à 365 jours), onglet Tendances sur 7/30/90 jours, graphique et journal quotidien UTC.
- Premières détections distinctes des publications ; mises à jour, recalculs, fermetures, réouvertures et résultats des scans comptés séparément.
- Lecture cohérente et bornée, erreurs explicites sans statistiques partielles ; une indisponibilité des tendances ne masque pas les offres.
- 1 362 tests réussis, couverture 96 %, contenu des 11 tables réelles préservé. Guide [TRENDS.md](TRENDS.md), bilan [VALIDATION-LOT24.md](VALIDATION-LOT24.md).

## Lot 25 — Édition locale des candidatures

- Deux sous-agents : service transactionnel et formulaire ; serveur HTTP, intégration et tests navigateur par l'agent principal.
- Mode explicite `dashboard serve --edit-applications` ; statuts, dates, contact, notes et prochaine action modifiables depuis la fiche.
- Historique avant/après, garde des brouillons, contrôle des conflits avec les autres fenêtres et les éditions CLI. Aucun renvoi automatique en cas de réponse incertaine.
- Origine locale et jeton par session, formulaires bornés et validés, lecture seule préservée pour le serveur par défaut et les exports.
- Guide [DASHBOARD-EDITING.md](DASHBOARD-EDITING.md), bilan [VALIDATION-LOT25.md](VALIDATION-LOT25.md).

## Lot 26 — Préférences d'expérience et aperçu des scores

- Deux sous-agents : audit du corpus et correction du parseur ; aperçu en lecture seule, intégration et répétition du recalcul par l'agent principal.
- Préférences directement attachées reconnues pour les trois motifs historiques, dont `ideally`, sans généraliser aux rubriques complètes ou aux alternatives diplôme/expérience.
- Comparaison des 813 offres : neuf minima interprétés différemment, six fiches avec changement d'explication, un total passant de 70 à 75. Les autres exigences et exclusions restent applicables.
- `rescore --dry-run` : scores, explications et catégories avant/après, seuils actuels/projetés, sans migration, historique, CSV ou transport de notification.
- Guide [SCORING-AUDIT.md](SCORING-AUDIT.md), audit [EXPERIENCE-SCOPE-AUDIT-LOT26.md](EXPERIENCE-SCOPE-AUDIT-LOT26.md), bilan [VALIDATION-LOT26.md](VALIDATION-LOT26.md).

## Lot 27 — Intégrité Workday et audit borné Citi

- Trois sous-agents : intégrité du collecteur, sonde de recherche et inspection du runtime ; intégration, tests du scanner et mesures réelles par l'agent principal.
- Correspondance des titres, types des champs et unicité des identifiants vérifiés avant import. Trois scénarios d'échec puis de reprise préservent les offres et le suivi des candidatures.
- Sonde hors réseau par défaut, mesure explicite sans import et preuves immuables. `repo` et `securities finance` dépassent chacun le plafond de 200 résultats ; le gain de couverture reste inconnu, configuration inchangée.
- 1 609 tests réussis, couverture 96 %, contenu des 11 tables réelles préservé. Docker/Podman absents et WSL non installé, validation conteneur toujours à effectuer.
- Guides [WORKDAY-QUERY-PROBE.md](WORKDAY-QUERY-PROBE.md), [WORKDAY-INTEGRITY-LOT27.md](WORKDAY-INTEGRITY-LOT27.md), bilan [VALIDATION-LOT27.md](VALIDATION-LOT27.md).

## Lot 28 — Conservation des sauvegardes et audit des qualifications

- Trois sous-agents : moteur de conservation, commande et documentation, audit des qualifications ; intégration, récupération réelle et vérification globale par l'agent principal.
- `backup plan` : inventaire vérifié, conservation par dernières archives/jours UTC/semaines ISO, motifs et volume des candidats. Une archive invalide bloque les recommandations ; aucune suppression implémentée.
- Nouvelle sauvegarde de 813 offres, restaurée vers une copie distincte : onze tables identiques à la base active. Les deux archives locales sont valides et conservées par la politique par défaut.
- Audit de 813 descriptions et neuf cas vérifiés : prochain correctif local proposé pour `Experience Desirable:` ; aucune modification des scores dans ce lot.
- Guide [BACKUP-RETENTION.md](BACKUP-RETENTION.md), audit [QUALIFICATION-AUDIT-LOT28.md](QUALIFICATION-AUDIT-LOT28.md), bilan [VALIDATION-LOT28.md](VALIDATION-LOT28.md).

## Lot 29 — Préférences et expérience ajoutée au diplôme

- Trois sous-agents : préférence `Experience Desirable:`, expérience additive au diplôme et régressions indépendantes ; intégration et application contrôlée par l'agent principal.
- Deux extractions corrigées sur 813 offres : CA `[1]` → `[]` sans changement de score ; Susquehanna `[]` → `[7]`, score 65 → 0. Les alternatives ambiguës et les exigences indépendantes sont couvertes par des contre-exemples.
- Recalcul sans initialisation Telegram ; sauvegarde, répétition puis application d'une seule modification. Huit tables et toutes les autres données des offres préservées ; exports actualisés.
- 1 779 tests réussis, couverture 96 %. Base à 813 offres, 811 actives, 163 scores ≥70 et 249 ≥55.
- Guides [DEGREE-EXPERIENCE-LOT29.md](DEGREE-EXPERIENCE-LOT29.md), [QUALIFICATION-REGRESSIONS-LOT29.md](QUALIFICATION-REGRESSIONS-LOT29.md), bilan [VALIDATION-LOT29.md](VALIDATION-LOT29.md).

## Lot 30 — Filtres Workday et mesures ciblées Citi

- Deux sous-agents : options du collecteur, sonde et documentation ; découverte publique, mesures et intégration par l'agent principal.
- `applied_facets` et `--facet KEY=VALUE` : validation stricte, filtres conservés dans les preuves, copies indépendantes, limites et absence de fermeture par recherche partielle conservées.
- Quatre recherches Citi paginées dans Institutional Trading et Management Development Programs : 26 chemins distincts retenus, tous déjà connus ; aucun détail connu relu et aucun import.
- Configuration active inchangée, onze tables préservées ; 1 849 tests réussis, couverture 96 %.
- Guide [WORKDAY-QUERY-PROBE.md](WORKDAY-QUERY-PROBE.md), mesure [CITI-FACET-SCOPE-LOT30.md](CITI-FACET-SCOPE-LOT30.md), bilan [VALIDATION-LOT30.md](VALIDATION-LOT30.md).

## Lot 31 — Aperçu de collecte avant import

- Un sous-agent pour le moteur et ses tests ; commande, parcours de reprise, mesure réelle et validation globale par l'agent principal.
- `scan --dry-run` : collecte sur copie temporaire vérifiée, comparaison des événements et scores, aucune notification ni modification de la base active.
- Erreurs de sources explicites, limites de volume, WAL inclus et absence de fermeture par recherche partielle conservée.
- Guide [SCAN-PREVIEW.md](SCAN-PREVIEW.md), bilan [VALIDATION-LOT31.md](VALIDATION-LOT31.md).

## Lot 32 — Actualisation Greenhouse et comparaison des champs

- Deux sous-agents : champs modifiés dans l'aperçu et audit qualité ; capture publique, sauvegarde, répétition, import et vérification par l'agent principal.
- Cinq catalogues, 486 annonces publiques, 89 retenues. Une nouvelle DRW Floor Trader à Chicago, début été 2027, score actuel 79 ; aucune mise à jour de contenu ni fermeture des offres existantes.
- `changed_fields` explique les événements d'aperçu sans exposer les descriptions ou notes. Audit des 88 offres antérieures et revue distincte de la nouvelle offre.
- Base à 814 offres, 812 actives, 164 scores actifs ≥70 et 250 ≥55 ; 813 suivis précédents préservés, exports actualisés.
- Bilan [VALIDATION-LOT32.md](VALIDATION-LOT32.md), audit [GREENHOUSE-QUALITY-LOT32.md](GREENHOUSE-QUALITY-LOT32.md).

## Lot 33 — Indice junior DRW campus

- Deux sous-agents : reconnaissance des preuves campus et régressions indépendantes ; comparaison des 814 offres, intégration et correction locale par l'agent principal.
- Indice junior seulement avec Campus, Full-time et exigence de diplôme attendu dans une rubrique candidat reconnue. Stages, préférences et mentions génériques ne suffisent pas.
- Une seule offre modifiée : DRW Floor Trader, score 79 → 94. Dates de collecte, candidatures et alertes préservées ; aucune requête réseau supplémentaire.
- Audit [DRW-CAMPUS-AUDIT-LOT33.md](DRW-CAMPUS-AUDIT-LOT33.md), bilan [VALIDATION-LOT33.md](VALIDATION-LOT33.md).

## Lot 34 — Preuves d'actifs et de profil DRW

- Trois sous-agents : helper de filtrage, audit/régressions indépendantes et stabilisation d'un test HTTP ; intégration du score, comparaison des 814 offres et recalcul par l'agent principal.
- Deux passages exacts de présentation DRW retirés de la seule vue de calcul actifs/profil. Missions avant/après et descriptions stockées conservées ; aucune troncature générale.
- 27 explications, 25 listes d'actifs et neuf scores totaux corrigés. Floor Trader 94 → 82, junior 20/20 préservé ; 787 offres hors DRW inchangées.
- Base à 814 offres, 812 actives, 163 scores actifs ≥70 et 250 ≥55. Huit tables, dates de collecte et suivi préservés ; exports actualisés.
- Audit [DRW-EVIDENCE-AUDIT-LOT34.md](DRW-EVIDENCE-AUDIT-LOT34.md), bilan [VALIDATION-LOT34.md](VALIDATION-LOT34.md).

## Lot 35 — Expérience visible et filtrable

- Trois sous-agents : calcul et tests, interface, audit/régressions indépendantes ; intégration et vérification navigateur par l’agent principal.
- Minimum reconnu affiché dans chaque ligne et fiche. Filtre 0–2 ans, >2 ans ou non reconnu, combinable avec les autres critères ; absence de minimum distincte d’un zéro explicite.
- Sur les 163 offres prioritaires actives : 21 minima de 0–2 ans, six de trois ans et 136 non reconnus. L’indicateur ne garantit pas l’éligibilité.
- 2 068 tests réussis, couverture 96 %. Parcours Edge sur ordinateur/mobile et serveur local vérifiés ; onze tables et CSV inchangés. Export HTML actualisé.
- Audit [EXPERIENCE-VISIBILITY-LOT35.md](EXPERIENCE-VISIBILITY-LOT35.md), bilan [VALIDATION-LOT35.md](VALIDATION-LOT35.md).

## Lot 36 — CI sur installation propre et Docker Linux

- Deux sous-agents : correction des imports pytest et audit indépendant Docker/CI ; intégration et validation réelle GitHub par l’agent principal.
- Import des utilitaires de test corrigé pour l’entrée console pytest. Paquet non éditable, matrice Python complète et artefacts conservés 14 jours.
- 2 068 tests réussis sur chacune des versions Python 3.11 à 3.14 sous Ubuntu, couverture 96 %, ainsi que sous Windows 3.14.
- Build Docker, ENTRYPOINT et reprise validés : UID 10001, réseau coupé, huit offres synthétiques, onze tables restaurées identiques, volume de test nettoyé.
- Données locales et CSV préservés. Docker Desktop installé ; activation WSL et exploitation sur l’hôte cible restent à faire.
- Bilan et preuves [VALIDATION-LOT36.md](VALIDATION-LOT36.md).

## Lot 37 — Fourchettes d’expérience et revue des rôles hybrides

- Trois sous-agents : audit/régressions, helper et audit métier/revue d’impact ; intégration et recalcul contrôlé par l’agent principal.
- Fourchettes explicites sans signe + reconnues, avec bornes basses et protection des préférences, négations, alternatives et contextes d’entreprise.
- 32 extractions, 15 explications et sept scores corrigés sur 814 offres ; sauvegarde, répétition, application et idempotence vérifiées. Huit tables et toutes les données source préservées.
- Base à 812 offres actives, 161 prioritaires et 246 pertinentes ; CSV et dashboard actualisés. 2 152 tests réussis localement et sur chacune des quatre versions Python de la CI, couverture 96 % ; Docker et reprise validés.
- Audit de sept rôles hybrides : aucune levée d’exclusion isolée justifiée, notamment en raison d’exigences d’expérience et d’un stage explicite à préserver.
- Bilan [VALIDATION-LOT37.md](VALIDATION-LOT37.md), audits [EXPERIENCE-GAPS-LOT37.md](EXPERIENCE-GAPS-LOT37.md) et [HYBRID-ROLE-AUDIT-LOT37.md](HYBRID-ROLE-AUDIT-LOT37.md).

## Lot 38 — Stages dans les descriptions et audit des exigences restantes

- Trois sous-agents : audit/régressions indépendantes, helper de détection et audit des formulations d’expérience restantes ; intégration et recalcul contrôlé par l’agent principal.
- Stages Jane Street reconnus à partir de formulations directes adressées au candidat, uniquement sur la source officielle auditée. Citations, expériences passées, recrutement et encadrement de stagiaires protégés.
- 45 motifs d’exclusion ajoutés, six scores corrigés ; 769 autres offres strictement inchangées. Sauvegarde, restauration, répétition, application et idempotence vérifiées ; candidatures et données source préservées.
- Base à 812 offres actives, 161 prioritaires et 240 pertinentes ; CSV, export HTML et serveur local actualisés. 2 229 tests réussis localement et sur Python 3.11 à 3.14 en CI, couverture 96 % ; parcours Edge, build Docker et reprise vérifiés.
- Sept qualifications avec `years in` identifiées pour le prochain correctif ; durées contractuelles et parcours académiques séparés. Aucune extension du parseur d’expérience dans ce lot.
- Bilan [VALIDATION-LOT38.md](VALIDATION-LOT38.md), audits [INTERNSHIP-AUDIT-LOT38.md](INTERNSHIP-AUDIT-LOT38.md) et [EXPERIENCE-IN-AUDIT-LOT38.md](EXPERIENCE-IN-AUDIT-LOT38.md).

## Lot 39 — Expérience professionnelle formulée avec « years in »

- Trois sous-agents : implémentation, tests/revue d’impact indépendants, audit de deux cas ambigus ; mesure, recalcul et validation par l’agent principal.
- Formes `N–M years in` et `N+ years in` reconnues dans des qualifications et domaines professionnels audités. Préférences, négations, durées contractuelles et alternatives protégées.
- Sept indicateurs auparavant inconnus précisés : quatre Optiver et deux IMC/Jump à trois ans, UBS à sept ans. Huit listes de minima textuels changent, sans abaisser le minimum Citi de dix ans.
- Sept décompositions corrigées, aucun score total changé ; 807 autres fiches strictement identiques. Sauvegarde restaurée, répétition et contrôle d’idempotence réussis.
- Base à 812 offres actives, 240 pertinentes et 161 prioritaires ; CSV, HTML et serveur local actualisés. 2 342 tests réussis localement et sur Python 3.11 à 3.14 en CI, couverture 96 % ; filtres et fiches vérifiés dans Edge, build Docker et reprise réussis.
- Audit Jump : la durée cinq est dérivée du texte par le collecteur et accepte l’académie ; provenance et signification doivent être distinguées avant une correction dédiée. Aucun changement des deux cas ambigus dans ce lot.
- Bilan [VALIDATION-LOT39.md](VALIDATION-LOT39.md), audit [AMBIGUOUS-EXPERIENCE-LOT39.md](AMBIGUOUS-EXPERIENCE-LOT39.md).

## Lot 40 — Provenance et cadre des exigences Jump

- Trois sous-agents : modèle/collecteur, présentation, audit/régressions indépendantes ; correction contrôlée et validation par l’agent principal.
- Preuves typées avec durée, cadre, origine et extrait exact ; compatibilité des anciens JSON. Collectes et aperçu historisent aussi les changements de preuve seuls.
- Deux fiches corrigées après sauvegarde/restauration : Hong Kong garde une preuve cinq ans industrie/académie avec minimum professionnel inconnu ; New York/Chicago conserve deux ans professionnels. Une décomposition modifiée, zéro total changé, 812 autres lignes identiques.
- Dashboard et exports actualisés, 812 offres actives, 240 pertinentes et 161 prioritaires. Preuves affichées en texte ; parcours Edge ordinateur/mobile et compatibilité des données vérifiés. 2 438 tests réussis localement et sur Python 3.11 à 3.14 en CI, couverture 96 % ; build Docker et reprise validés.
- Bilan [VALIDATION-LOT40.md](VALIDATION-LOT40.md), audit [EXPERIENCE-PROVENANCE-LOT40.md](EXPERIENCE-PROVENANCE-LOT40.md).

## Lot 41 — Provenance Crédit Agricole CIB et minimum Macquarie

- Sous-agents pour les collecteurs, les audits/revue indépendante et les parcours navigateur ; intégration, correction et validation par l’agent principal.
- 21 preuves du champ employeur Crédit Agricole ajoutées avec minima et scores inchangés. Une exigence Macquarie de cinq ans en sales trading devient explicite, score 71 → 0 ; provenance et extraits visibles dans le dashboard.
- Impact des 814 offres revu indépendamment, sauvegarde restaurée, répétition puis application de 22 corrections. 792 autres lignes et huit tables préservées, deuxième passage sans effet.
- Base à 812 actives, 239 pertinentes et 160 prioritaires ; CSV, HTML et serveur local actualisés. 2 587 tests réussis localement et sur Python 3.11 à 3.14 en CI, couverture 96 % ; parcours Edge ordinateur/mobile et 20 variantes de données validés, build Docker et reprise réussis. Aucune actualisation des pages employeur : dates de collecte conservées.
- Audit Nomura : sept minima reproduits sur 16 offres, sans erreur réelle démontrée. Protections et provenance restent à compléter avant extension.
- Bilan [VALIDATION-LOT41.md](VALIDATION-LOT41.md), audits [Crédit Agricole](CA-EXPERIENCE-PROVENANCE-LOT41.md), [Macquarie](MACQUARIE-EXPERIENCE-PROVENANCE-LOT41.md), [Nomura](NOMURA-EXPERIENCE-PROVENANCE-LOT41.md).

## Lot 42 — Actualisation Greenhouse et exigences IMC

- Cinq catalogues publics archivés : 509 annonces, 90 retenues, six ajouts et deux descriptions modifiées. Aperçu examiné, sauvegarde restaurée, répétition puis import ; aucun échec, alerte ou fermeture déduite d’une absence.
- Variante de rubrique IMC `Your Skills & Experience` reconnue : minimum de trois ans conservé malgré la reformulation de la page. Aucun effet sur les 814 offres antérieures ; mesure des 90 entrantes.
- Réponse 405 du serveur en lecture seule fiabilisée sous Windows avec lecture bornée des petits corps ; absence d’envoi complet et corps de 8 192 octets testés.
- 814 suivis et scores antérieurs préservés ; 730 lignes d’offres strictement identiques. Base à 820 offres, 818 actives, 243 pertinentes et 162 prioritaires ; exports et serveur local actualisés. Cinq sources fraîches sur 24.
- 2 604 tests réussis localement et sur Python 3.11 à 3.14 en CI, couverture 96 % ; parcours Edge ordinateur/mobile, build Docker et reprise validés. Revue des six nouvelles offres : contraintes d’expérience, doctorat et dates anciennes documentées ; limites de classement DRW à auditer séparément.
- Bilan [VALIDATION-LOT42.md](VALIDATION-LOT42.md).

## Lot 43 — Actualisation Workday et grades seniors explicites

- Quatre sources publiques actualisées : Barclays, Deutsche Bank, Morgan Stanley et Citi. Recherche `trading` conservée, 1 902 résultats, 110 fiches retenues, 211 requêtes ; 14 ajouts et huit mises à jour après revue, sauvegarde restaurée et répétition.
- Sept grades seniors explicites reconnus dans les champs audités ; trois anciens scores passent à zéro. Acronyme ED seul, citations et mentions d’un collègue insuffisants ; aucune expérience minimale déduite du grade.
- 820 suivis préservés et 724 anciennes lignes strictement identiques. Les 29 annonces absentes restent actives avec leur ancienne date ; aucune clôture ou alerte. Rejeu d’aperçu sans changement.
- Base à 834 offres, 832 actives, 246 pertinentes et 166 prioritaires ; CSV, HTML et serveur local actualisés. Neuf sources fraîches, quinze à actualiser.
- 2 652 tests réussis localement et sur Python 3.11 à 3.14 en CI, couverture 96 %, Ruff et mypy validés ; parcours Edge ordinateur/mobile, quatre fiches seniors et vingt variantes de preuves vérifiés. Build Docker et reprise sous UID 10001 réussis, onze tables restaurées identiques.
- Deux formulations d’expérience DB encore non reconnues identifiées pour le prochain correctif borné. Bilan [VALIDATION-LOT43.md](VALIDATION-LOT43.md).

## Lot 44 — Commandes Telegram et incidents

- Alertes d'offres en français, dates connues, expérience reconnue, score
  détaillé et extrait employeur dans sa langue d'origine.
- `/status`, `/help` et `/start` privés, sans modification des candidatures.
  Signal périodique du collecteur et notifications d'incident avec stabilité
  minimale de deux minutes et espacement minimal de trente minutes.
- Service Telegram indépendant installé comme quatrième tâche Windows.
  Menu vérifié via Telegram ; premier avis d'incident accepté. La surveillance
  de l'arrêt complet du PC demande toujours un système externe.
- Refus HTTP du dashboard éditable fiabilisés sous Windows.
  2 720 tests réussis localement et sur Python 3.11 à 3.14 en CI,
  couverture 96 % ; Docker et reprise des onze tables réussis.
- Guide [TELEGRAM-CONTROL.md](TELEGRAM-CONTROL.md),
  bilan [VALIDATION-LOT44.md](VALIDATION-LOT44.md).

## Lot 45 — Consultation des offres dans Telegram

- `/top` : jusqu'à cinq meilleures offres à examiner ; `/new` : découvertes
  des dernières 24 heures, triées de la plus récente à la plus ancienne.
- Score, minimum d'expérience reconnu, dates de découverte/vérification,
  échéance avec précision préservée et lien complet. Nombre total de
  correspondances explicite, réponse bornée à un message.
- Lecture seule ; réutilisation de la validation du dashboard. Sources et
  fiches récentes exigées, candidatures déjà envoyées et échéances dépassées
  ou ambiguës exclues. Aucune modification du score ou du suivi.
- Guide [TELEGRAM-CONTROL.md](TELEGRAM-CONTROL.md).
  Le digest est ajouté au lot 46 ; les actions de suivi depuis Telegram restent à faire.
- Déployé sur ce poste ; 2 761 tests réussis sous Windows et sur Python
  3.11 à 3.14 en CI, couverture 96 %.
  Build Docker et restauration des onze tables synthétiques validés.
  Bilan [VALIDATION-LOT45.md](VALIDATION-LOT45.md).

## Lot 46 — Récapitulatif Telegram quotidien

- `/digest` pour prévisualiser ; `/digest_on HH:MM` pour activer/régler ;
  `/digest_off` pour désactiver. Réglages privés persistants, sans écriture métier.
- Découvertes pertinentes des 24 dernières heures et bref état des sources,
  selon les mêmes critères que `/new`. Message explicite même sans nouvelle offre.
- Heure de Paris avec passage été/hiver ; début au prochain créneau à venir,
  rattrapage limité à quatre heures et une tentative enregistrée par date avant
  envoi. Aucune répétition automatique après livraison incertaine.
- Guide [TELEGRAM-CONTROL.md](TELEGRAM-CONTROL.md).

## Les cinq améliorations prioritaires après le lot 46

1. **Valider l’exploitation continue** : depuis le 24 septembre, le collecteur et le dashboard tournent via des tâches Windows natives, avec démarrage à l’ouverture de session, reprise après échec et sauvegarde locale quotidienne vérifiée. Telegram est activé après accusé positif du message de test privé. Voir [exploitation Windows](WINDOWS-LIVE.md). Restent la surveillance prolongée, les incidents BNP/DB/UBS du premier lancement et la copie distante des sauvegardes. Docker Linux reste validé en CI et sur le poste via WSL 2 ; aucun VPS n’est provisionné.
2. **Corriger les exigences observées et étendre la provenance** : priorité aux nouvelles fiches DB `R0452740` (`three (3) years`) et `R0450097` (`1-4 years of prior work experience`) dont les minima restent non reconnus au lot 43. Prévoir protections des préférences, négations et alternatives, puis mesure sur toute la base avant correction. Ensuite reprendre les libellés Nomura `Position Specifications → Experience` et la provenance des 16 offres ; aucune erreur des sept minima existants n’est démontrée. Les lots 39–41 couvrent déjà les qualifications `years in`, Jump, Crédit Agricole et Macquarie. Le cas Jane Street HR et les rôles hybrides IMC/Jump/Research Analyst/Trading Assistant restent à qualifier ; ne pas lever leurs exclusions globalement. Revoir Citadel lorsque son accès public redevient disponible.
3. **Explorer les lacunes Workday** : catégories supplémentaires, portails early careers et confirmations explicites de clôture. Le cache mesuré au lot 23 reste désactivé faute de bénéfice ; conserver les budgets et les conclusions du lot 15 avant d'ajouter des requêtes.
4. **Poursuivre l'audit des sources** : continuer les actualisations bornées avec aperçu d’impact sur les quinze sources restantes. Le lot 42 a rafraîchi IMC, DRW, Flow, Jump et XTX ; le lot 43 ajoute les quatre banques Workday. Les cinq absentes Greenhouse et 29 absentes Workday n’ont pas été clôturées ni artificiellement rafraîchies. Examiner séparément les nouveaux cas DRW `Quant Researcher` et `Junior Trader` présent dans la description, ainsi que l’affichage des prérequis de diplôme. Le lot 30 a terminé quatre recherches Citi filtrées sans nouveau chemin retenu ; les autres catégories et la recherche `structuring` restent hors de cette mesure. Reprendre JPMorgan lorsque son accès public devient disponible. Aucune exhaustivité globale n'est revendiquée.
5. **Préparer l'exploitation régulière** : tests prolongés et copie distante vérifiée. Le lot 28 fournit un plan de conservation sans suppression ; son application éventuelle reste à concevoir. Le dashboard dispose de statistiques historiques et d'un suivi éditable localement ; une exploitation sur plusieurs postes demanderait un mode d'accès adapté.

## Phase 2 — Employeurs

Ordre prévu : Goldman Sachs, JPMorgan, Morgan Stanley, Citi, Barclays, Deutsche Bank, UBS, BNP Paribas, Société Générale, Crédit Agricole CIB, HSBC, Macquarie, Nomura. Puis Jane Street (déjà une première source), Citadel Securities, Optiver, IMC, DRW, SIG, Flow Traders, Jump Trading et XTX Markets.

La liste de banques et sociétés plus large du master prompt reste la cible à terme. La présence d'un nom dans cette feuille de route ne signifie pas que ses offres sont actuellement surveillées.

## Phase 3

Dashboard en lecture seule livré au lot 22, statistiques historiques au lot 24, suivi interactif local au lot 25 ; rappels conditionnels livrés au lot 17. Restent l'enrichissement IA facultatif, le résumé des postes et le matching CV. Les fonctions de candidature automatique, les recherches de contacts privés et les prédictions de calendrier ne font pas partie de ce premier lot.
