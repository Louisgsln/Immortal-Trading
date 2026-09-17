# Couverture vérifiée des sources

État au 17 septembre 2026. « Activée » signifie incluse dans `scan` / `watch`, pas qu'un watcher tourne actuellement.

| Employeur | Portail public | Connecteur | Configuration |
|---|---|---|---|
| Deutsche Bank | [DBWebsite](https://db.wd3.myworkdayjobs.com/DBWebsite) | Workday CXS | Activée |
| Morgan Stanley | [External](https://ms.wd5.myworkdayjobs.com/External) | Workday CXS | Activée |
| Citi | [2](https://citi.wd5.myworkdayjobs.com/2) | Workday CXS | Activée |
| Barclays | [External Career Site](https://barclays.wd3.myworkdayjobs.com/External_Career_Site_Barclays) | Workday CXS | Activée |
| Jane Street | [Open roles](https://www.janestreet.com/join-jane-street/open-roles/) | Greenhouse | Activée |
| Goldman Sachs | [Higher](https://higher.gs.com/results) et [Campus](https://higher.gs.com/campus) | Recherche GraphQL publique et fiches HTML | Deux sources activées |
| BNP Paribas | [Toutes les offres](https://group.bnpparibas/emploi-carriere/toutes-offres-emploi) | HTML et JobPosting | Activée, recherche Trading |
| UBS | [Recherche officielle](https://www.ubs.com/global/en/careers/search-jobs.html) | Tableaux publics BrassRing | Deux sources activées : étudiants/graduates et professionnels |
| Société Générale | [Répertoire FR](https://careers.societegenerale.com/fr/Technical/toutes-les-offres) et [EN](https://careers.societegenerale.com/en/Technical/all-job-offers) | Répertoires publics HTML et fiches détaillées | Activée, filtrage Trading/Markets |
| Crédit Agricole CIB | [Offres publiques](https://jobs.ca-cib.com/pages/offre/listeoffre.aspx) | Catalogue Talentsoft et fiches HTML | Activée, filtrage Trading/Markets |
| HSBC | [Programme finder](https://www.hsbc.com/careers/students-and-graduates/find-a-programme) et [professionnels](https://portal.careers.hsbc.com/careers) | Catalogue campus SuccessFactors et recherche professionnelle Eightfold | Deux sources activées : étudiants/graduates et professionnels |
| Macquarie | [Job Search](https://recruitment.macquarie.com/en_US/careers/SearchJobs/) | Avature HTML public | Activée, recherche Trading |
| Nomura | [Campus](https://www.nomura.com/careers/early-careers/apply-to-nomura/) et [professionnels](https://careers.nomura.com/Nomura?locale=en_US) | Oleeo campus et SuccessFactors professionnel | Deux sources activées |
| Optiver | [Jobs](https://www.optiver.com/join-us/jobs) | API publique du site et fiches HTML | Activée, filtrage Trading/Markets |
| IMC | [Search careers](https://www.imc.com/us/search-careers) | Greenhouse public `imc`, catalogue global | Activée, filtrage Trading/Markets |
| DRW | [Listings](https://www.drw.com/work-at-drw/listings) | Greenhouse public `drweng`, tableau anglais | Activée, filtrage Trading/Markets |
| SIG / Susquehanna | [Jobs](https://careers.sig.com/jobs) | Catalogue iCIMS/Jibe public | Activée, Trading/Markets ; filtres de fonction et de catégorie |
| Flow Traders | [Job search](https://www.flowtraders.com/careers/job-search/) | Greenhouse public `flowtraders` | Activée, Trading/Markets ; Events exclu |
| Jump Trading | [Careers](https://www.jumptrading.com/careers) | Greenhouse public `jumptrading` | Activée, Trading/Markets ; contrats Campus/Experienced/Intern |
| XTX Markets | [Careers](https://www.xtxmarkets.com/careers/) | Greenhouse public `xtxmarketstechnologies` | Activée, Trading/Markets ; preuve de missions pour Trading Tech |
| Citadel Securities | [Open opportunities](https://www.citadelsecurities.com/careers/open-opportunities/) | Non implémenté | Désactivée, HTTP 403 |
| JPMorgan | [Candidate Experience](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/) | Oracle Candidate Experience | Désactivée, HTTP 403 ; tests hors réseau |

L'audit hors ligne de toutes les sources et la comparaison des requêtes Workday sont disponibles depuis le lot 15. La suite porte sur les sources encore anciennes et les titres techniques manqués. Citadel Securities reste à valider lorsque son accès public sera disponible. Aucun flux n'est supposé disponible sans vérification.

## Lot 32 — Actualisation des cinq tableaux Greenhouse filtrés

Catalogues relus le 17 septembre 2026 à 06:56 UTC, avec robots et espacement :
IMC 174 annonces/26 retenues, DRW 154/27, Flow Traders 40/10, Jump 108/25 et XTX 10/1.
Six requêtes publiques réussies au total. Les réponses vérifiées sont rejouées
localement pour l'aperçu, la répétition et l'import, sans nouvelle requête.

Une seule nouvelle identité : [DRW Floor Trader, Chicago](https://job-boards.greenhouse.io/drweng/jobs/8207750),
temps plein, catégorie Campus, début cible été 2027, diplôme attendu entre décembre
2026 et juin 2027. Aucune mise à jour de contenu ni fermeture des 88 offres
précédentes. Le filtre reste partiel et n'infère pas de fermeture par absence.
Le score initial de 79 sous-pondérait l'indice junior ; cette limite est documentée
dans l'[audit qualité](GREENHOUSE-QUALITY-LOT32.md). Le lot 33 apporte un indice
junior contrôlé et porte ce score à 94, sans nouvelle collecte ni modification de
date de début. Le lot 34 écarte ensuite les actifs du texte général DRW et donne
un score de 82, en conservant l'indice junior. Bilans : [lot 32](VALIDATION-LOT32.md),
[lot 33](VALIDATION-LOT33.md), [lot 34](VALIDATION-LOT34.md).

## Lot 15 — Audit de fraîcheur et recherches Workday

**Échéances, lot 17 :** les descriptions déjà conservées peuvent maintenant fournir une deadline dérivée via `deadlines list`, avec preuves et précision. Six instants supplémentaires sont reconnus chez Nomura campus, Citi et Optiver ; cinq dates restent sans heure/fuseau. Les champs structurés et règles propres aux portails décrits ci-dessous ne sont pas réinterprétés. Aucun portail n'a été rescanné pour cette analyse locale. Voir [VALIDATION-LOT17.md](VALIDATION-LOT17.md).

**Actualisation du lot 16, 17 septembre 2026 à Paris :** Goldman professionnels (68 fiches reçues, trois nouvelles), Goldman campus (30 reçues, aucune nouvelle) et Jane Street (230 reçues, deux nouvelles) ont été rescannés. L'audit final indique 24 sources activées récentes au seuil de 24 h. Le second passage est stable sur les nouvelles fiches et modifications ; deux anciennes fiches Jane Street sont fermées après deux absences du catalogue complet. Les cinq absentes de Goldman professionnels restent conservées, cette recherche étant partielle. Détails dans [VALIDATION-LOT16.md](VALIDATION-LOT16.md). Ce bilan ne correspond pas à une surveillance continue.

`trading-radar audit --max-age-hours 24` utilise une connexion SQLite `mode=ro`, avec une transaction de lecture commune aux états des sources et aux observations. Une source fraîche peut conserver des fiches anciennes : `recently_seen_jobs` et `not_recently_verified_jobs` portent sur la dernière observation de chaque fiche dans cette source. Les sources désactivées et celles absentes de la configuration restent visibles. Aucun timestamp n'est rafraîchi par l'audit, aucun catalogue absent n'est créé et aucun état d'ouverture n'est déduit.

Le 17 septembre 2026 à Paris, `scripts/audit_workday.py` a comparé `trading`, `trader`, `structuring`, `repo` et `securities finance` sur les portails publics, avec le client HTTP, les règles robots et les limites du connecteur. Les fiches supplémentaires sont lues et scorées sans import. Résultats locaux dans `data/discovery/lot15/`, ignorés par Git ; bilan durable dans [VALIDATION-LOT15.md](VALIDATION-LOT15.md).

| Source | Titres retenus par Trading | Suppléments distincts des autres requêtes | Suppléments avec score > 0 | État de l'audit réseau |
| --- | ---: | ---: | ---: | --- |
| Barclays | 22 | 6 | 0 | Cinq requêtes parcourues |
| Deutsche Bank | 22 | 7 | 0 | Cinq requêtes parcourues |
| Morgan Stanley | 20 | 3 | 0 | Cinq requêtes parcourues |
| Citi | 57 | 0 pour Trader | Non mesuré au-delà | Structuring dépasse 1 999 résultats ; Repo et Securities Finance non parcourues |

Les 16 suppléments évalués concernent notamment des stages, l'investment banking, le financement d'infrastructure, le support ou des fonctions Capital Markets sans rôle de trading établi par le classement actuel. Cela ne prouve ni l'exhaustivité de Trading ni l'absence d'intérêt de ces postes pour un autre profil. Aucune nouvelle requête n'est activée dans ce lot ; la limite Citi n'est pas relevée. Un même chemin Workday avec des titres différents entre requêtes fait désormais échouer la collecte avant import. Les recherches restent partielles, sans fermeture par absence.

## Lot 14 — Nomura professionnels

Vérifié le 17 septembre 2026. La [page officielle des professionnels en Asie](https://www.nomura.com/asia/careers/experienced-professionals/) lie le portail `careers.nomura.com/Nomura`. Son formulaire GET utilise `/Nomura/search/?q=trading`. Les 337 résultats observés sont paginés par 100 avec `startrow` : le connecteur contrôle le mot recherché, les bornes affichées, le total, les doublons et la cohérence de la première page relue après parcours. Les versions mobile et ordinateur d'une même carte doivent concorder.

Les titres sont filtrés localement, avec `etrading` ajouté explicitement. La division Operations est écartée : Trading Controls Associate appartient à cette division. Les annonces conservées sont vérifiées sur leur fiche JobPosting : référence de l'URL canonique et du lien de candidature, titre, employeur, adresse, description complète et date de publication UTC. Le formulaire de candidature n'est jamais ouvert ni envoyé. Laser Digital et les portails japonais distincts ne sont pas couverts.

Le libellé Corporate Title dans la description fournit un indice de séniorité. VP/AVP/Director/ED/MD entraînent une exclusion senior, même si le titre de l'annonce ne le montre pas. Analyst apporte un indice junior ; Associate seul reste sans indice junior supplémentaire. Le minimum est extrait d'une rubrique explicite Experience, par exemple 2–4 ans. Ces données n'annulent pas les exclusions du score. Les références distinctes portant un même titre GM-Global Markets ne sont pas fusionnées.

Temp Analyst (Structuring), à Séoul, annonce explicitement un contrat de douze mois ; celui-ci est conservé sans devenir un programme graduate ni une prise de poste 2027. `datePosted` au format UTC est une publication ; `validThrough` reste dans le payload brut optionnel, sans être converti en deadline candidat. Aucun début d'emploi n'est inventé.

Le titre Lead Support Analyst identifie ici du support informatique et est exclu du classement prioritaire. Le filtre ne rejette pas tous les Trading Support : les deux fiches inspectées couvrent du quant eFX et du financement de titres. Le titre reste une approximation de la fonction réelle ; les postes sans termes Trading/Markets/Structuring attendus peuvent être manqués. Collecte partielle (`complete=False`), sans clôture sur absence. Bilan : [VALIDATION-LOT14.md](VALIDATION-LOT14.md).

## Lot 13 — UBS et HSBC professionnels

Vérifiés le 17 septembre 2026. La page UBS officielle distingue Professionals (`siteid=5012`, `LinkID=15231`) de Students and graduates (`5131`, `15232`). Le connecteur réutilise la lecture publique BrassRing existante, mais valide le site et le lien du bootstrap de chaque source. Les liens localisés doivent annoncer le bon `frmSiteId`. Le tableau professionnel est lu intégralement, puis les titres Trading/Markets sont filtrés localement. Session et contexte de recherche ne sont pas stockés avec les offres.

La page [HSBC Careers](https://www.hsbc.com/careers) oriente les pays vers `portal.careers.hsbc.com/careers`. Le JavaScript public appelle `GET /api/apply/v2/jobs?domain=hsbc.com&query=trading&start=0&num=10`. Le connecteur pagine par dix, vérifie le domaine, le mode anonyme, le mot recherché et l'absence de filtre géographique. Total, taille des pages et unicité des positions sont contrôlés ; la première page est relue après la pagination. Ce contrôle réduit le risque d'un catalogue mouvant sans constituer une garantie transactionnelle côté serveur.

Chaque position doit être une annonce ATS explicitement publique. Les résultats de la division `Intl Wealth & Premier Banking` sont écartés avant lecture des détails, conformément à l'exclusion de la gestion patrimoniale. Les fiches `/careers/job/ID` doivent confirmer identité, titre et lieux dans leurs données embarquées ainsi qu'un JobPosting complet. Les identifiants ATS sont conservés comme preuve ; l'identifiant de position Eightfold reste l'identité de collecte. Les données candidat, fonctions de candidature et recommandations personnalisées ne sont pas utilisées.

Les horodatages techniques `t_create`/`t_update` ne deviennent pas des dates de publication. Les dates JobPosting sans fuseau restent des valeurs brutes ; `validThrough` ne devient pas une deadline candidat. Aucun début 2027 ni niveau junior n'est supposé. Les titres hors périmètre et fonctions de vente pure peuvent rester en base avec score nul. Le filtre de titres laisse notamment certains postes Dealer ou intitulés techniques sans terme Trading/Markets hors collecte.

Les deux sources sont partielles (`complete=False`) : l'absence d'une fiche ne suffit pas à la fermer. Bilan : [VALIDATION-LOT13.md](VALIDATION-LOT13.md).

### Correction du lecteur robots

HSBC publie une interdiction générale suivie d'autorisations pour `/careers` et `/api/apply`. `urllib.robotparser` retenait la première règle correspondante. Protego ≥ 0.6.2 applique la règle la plus précise, les jokers, l'ancrage final et les groupes d'agent ; les chemins non autorisés restent interdits. Références : [RFC 9309, règles de correspondance](https://www.rfc-editor.org/rfc/rfc9309.html#section-2.2.2) et [Protego](https://pypi.org/project/Protego/0.6.2/). La version minimale inclut la correction du traitement des jokers publiée par le mainteneur.

Les refus HTTP 401/403 ne sont pas contournés et une politique robots inaccessible bloque toujours la source. Crawl-delay et espacement par hôte restent appliqués. Les tests vérifient aussi que les chemins interdits ne déclenchent aucune requête vers la page cible.

## Lot 12 — Jump Trading et XTX Markets

Vérifiés le 17 septembre 2026. Les pages [Jump étudiants](https://www.jumptrading.com/hr/students-new-grads) et [Jump expérimentés](https://www.jumptrading.com/hr/experienced-candidates) chargent le tableau Greenhouse `jumptrading`. Le connecteur contrôle les liens personnalisés `/hr/job?gh_jid=ID` et les contrats Full-time - Campus, Full-time - Experienced et Jump Trading - Intern. Campus justifie un niveau junior, pas une date de début. Les entités Jump Crypto/Capital et les viviers ne sont pas collectés.

La page [XTX Careers](https://www.xtxmarkets.com/careers/) lie le tableau `xtxmarketstechnologies` et son miroir JSON public. Les dix références concordent lors de la découverte. La collecte courante lit directement Greenhouse avec descriptions complètes. XTX publie explicitement `metadata: null`, valeur admise pour ce tableau seulement ; une clé manquante reste une erreur.

Pour un titre technique XTX sans mot Trading, le département Tradingdev ETD Tech et la mention de l'équipe de développement du trading dans la rubrique The Role doivent être présents ensemble. Cette preuve alimente `role_hint=trading_technology`. La présentation générique de l'entreprise, les qualifications seules et l'appartenance au département ne suffisent pas : la fonction ML Performance du même département est écartée. Les exclusions de titre configurées continuent de primer.

Les contrôles Greenhouse partagés restent applicables : total exact, identifiants uniques, employeur et domaine attendus, description et lieu non vides, limites de volume et durée. Les prospect posts sont exclus. Le périmètre est filtré : aucune fermeture déduite d'une absence. Résultats des deux imports dans [VALIDATION-LOT12.md](VALIDATION-LOT12.md).

## Origine de la découverte

- Deutsche Bank : [page de recherche officielle](https://careers.db.com/professionals/search-roles/) et offre publique Workday indexée sur le domaine de la banque.
- Morgan Stanley : [exemple d'offre publique](https://ms.wd5.myworkdayjobs.com/en-US/External/job/SRE-Application-Support-Engineer---AWS_PT-JR033495), puis interrogation de la recherche CXS publique du tenant `ms`.
- Citi : le bouton Apply de l'[offre Markets Full Time Analyst 2027 à Londres](https://jobs.citi.com/job/london/markets-sales-and-trading-full-time-analyst-london-united-kingdom-2027/287/100186099392) renvoie vers le tenant `citi`, site `2`.
- Barclays : le [site carrière officiel](https://search.jobs.barclays/search-jobs/careers/22545/1/1) lie le portail `External_Career_Site_Barclays`. Les portails nommés « Private » trouvés ailleurs ne sont pas utilisés.

Les recherches Workday testées répondent en JSON, sans session authentifiée ni clé API. Chaque lecture passe par la politique robots et la régulation HTTP communes du projet. Le connecteur utilise le POST **de recherche** de la page publique ; il n'accède ni au compte candidat ni aux fonctions de dépôt de candidature.

## Périmètre exact du lot 2

Pour les quatre banques Workday :

1. Rechercher `trading` dans le moteur du portail, qui peut trouver le mot dans le titre ou la description.
2. Lire toutes les pages de ce résultat, 20 offres par page.
3. Retenir les titres contenant trading, trader, markets, structuring, structurer, repo ou securities finance.
4. Écarter avant lecture des détails les titres explicitement operations, product control, compliance, audit, market risk, director, vice president, VP, SVP, AVP, head of ou senior.
5. Lire la description et les lieux de chaque poste retenu, puis appliquer le score commun et ses exclusions plus fines.

**Ce n'est pas l'inventaire complet des offres de ces banques.** Les annonces sans ces termes, certains portails early careers distincts et des catégories proches peuvent échapper au périmètre. Le champ `complete` reste donc `false` : une disparition de cette recherche ne prouve pas une fermeture. L'extension des requêtes doit être testée progressivement.

Les stages sont conservés lorsqu'ils entrent dans le périmètre mais exclus des alertes prioritaires par les règles de score. Les programmes VIE et les graduate programmes à temps plein restent admissibles.

## Réglages Workday

Les options sont validées et les clés inconnues refusées :

```yaml
options:
  search_terms: [trading]       # union de recherches, dédupliquée avant lecture des détails
  title_terms: [trading, trader, markets, structuring, structurer, repo, securities finance]
  exclude_title_terms: [operations, product control, compliance, audit, market risk, director, vice president, vp, svp, avp, head of, senior]
  max_results_per_query: 1999  # au-delà, la recherche échoue explicitement
  max_details: 250            # limite explicite, jamais une troncature silencieuse
  max_scan_seconds: 600
```

Le site carrière doit être la racine publique exacte, avec ou sans locale (`en-US`), sur un domaine `tenant.wdN.myworkdayjobs.com`. Les URLs de connexion, les routes de détail comme racine, les domaines arbitraires et les chemins sortant de `/job/` sont refusés.

### Dates

`jobPostingInfo.startDate` est utilisé comme date de publication, pas comme début de contrat. Le texte relatif « Posted 30+ Days Ago » n'est pas converti en fausse date précise. `endDate` reste dans le payload brut optionnel ; son interprétation comme échéance candidat est reportée, car il s'agit d'une date de fin de publication sans heure confirmée.

La lecture d'une description permet aussi de signaler les années contradictoires. Par exemple, une annonce dont le titre indique 2027 et le texte un début en 2026 reçoit une explication à vérifier et une note prudente sur la date de début.

### Fiabilité et fréquence

- Total lu sur la première page. Un `total=0` sur les suivantes est accepté avec le nombre de résultats attendu ; d'autres changements de total sont traités comme un snapshot instable.
- Une page courte, répétée, mal formée, un détail manquant ou une limite dépassée font échouer la source avant import. Pas de snapshot partiel présenté comme réussi.
- Les descriptions sont relues à chaque scan ; pas de cache susceptible de masquer leurs changements dans ce lot.
- Les requêtes d'une même banque sont espacées de deux secondes. Les banques sont traitées avec la concurrence bornée existante.
- L'intervalle configuré de cinq minutes court après la fin du scan. La latence réelle inclut donc la durée de collecte ; les grandes recherches Citi peuvent prendre plusieurs minutes. La détection en quelques minutes n'est pas garantie pour tout le périmètre.
- L'échec d'une banque laisse les autres s'exécuter. Le premier import réussi de chaque banque est silencieux.

## Vérification opérateur

```powershell
.\.venv\Scripts\python.exe -m trading_radar doctor
.\.venv\Scripts\python.exe -m trading_radar scan --source workday
.\.venv\Scripts\python.exe -m trading_radar scan --company "Citi"
.\.venv\Scripts\python.exe -m trading_radar rescore
```

`rescore` recalcule le classement existant hors réseau, conserve les dates d'observation, écrit l'historique du score et actualise le CSV sans alerte. Le watcher doit être arrêté pour prendre le verrou de la base.

Le script `scripts/probe_workday.py --source citi` effectue une vérification limitée aux deux premières pages. Ses réponses sont enregistrées localement dans `data/discovery/`, ignoré par Git. Cette sonde ne remplace pas le test d'import complet.


## Lot 3 — Goldman Sachs

Contrat vérifié le 15 septembre 2026 dans les scripts publics liés par `https://higher.gs.com/results`. Le connecteur envoie uniquement la requête GraphQL de lecture `GetRoles` à `https://api-higher.gs.com/gateway/api/v1/graphql`, sans compte, cookie ou clé. Les variables reproduisent la recherche du portail : pages de 20, index commençant à zéro, catégories `EARLY_CAREER` et `PROFESSIONAL`, recherche `trading`.

Les filtres de titres et budgets sont partagés avec Workday. Les résultats non publiés et les avis « Notice of Filing » sont ignorés. Chaque identifiant numérique `externalSource.sourceId` mène à une fiche `https://higher.gs.com/roles/{id}`. Sa donnée JSON embarquée `__NEXT_DATA__` contient le titre, les lieux, la description HTML et l'état de candidature. L'identifiant du détail doit correspondre à celui demandé ; les fiches sans description font échouer le scan. Une fiche indiquant explicitement que la candidature est inactive est ignorée, sans fermeture des anciennes données à partir de ce seul inventaire partiel.

Dans le lot 3, les catégories campus n'étaient pas couvertes ; leur ajout est décrit ci-dessous. Aucune date de publication n'est inventée. Les compétences et exigences restent extraites de la description via le score commun.

## Lot 4 — Campus Goldman

La source `goldman_campus` réutilise la recherche publique avec la catégorie `CAMPUS`, et les mêmes fiches `/roles/{id}`. Elle possède sa propre référence initiale silencieuse. Les recherches `trading` et `ficc` sont réunies et dédupliquées avant lecture des descriptions ; `ficc` est ajouté aux termes de titre autorisés. La recherche professionnelle existante conserve son périmètre.

Le champ campus `startDate` du moteur sert au calendrier d'affichage de l'annonce. Il n'est pas une preuve de début d'emploi et n'est pas copié dans `expected_start_date`. Les dates de diplomation ne sont pas non plus des débuts de contrat. Les années présentes dans le titre ou les descriptions restent des indices traités par le score commun.

Les Summer Analyst/Associate, stages et Off Cycle/OffCycle restent enregistrés lorsqu'ils entrent dans le périmètre, mais exclus des alertes prioritaires. Les New Analyst/New Associate ne sont pas exclus automatiquement. Le périmètre reste partiel : pas de fermeture par absence.

## Lot 4 — BNP Paribas

Le connecteur utilise le formulaire GET du portail français : `form[q]=trading`, `page=1`, puis les pages suivantes de dix offres. Les fiches peuvent concerner tous les pays. Chaque page doit afficher le mot-clé demandé, un total cohérent et le bon numéro de page. Le lien `rel=next` du site omet la recherche : le connecteur reconstruit donc chaque URL avec les mêmes paramètres, sans suivre aveuglément ce lien.

Les titres passent par le filtre Trading commun avant lecture des détails. La donnée structurée `JobPosting` fournit l'identifiant employeur, la description HTML complète, les lieux, le type de contrat et `datePosted`. L'URL du détail doit correspondre exactement à la fiche demandée sur le domaine officiel. Données manquantes, changement de total, page courte, doublon ou budget dépassé font échouer la source avant import.

Les filiales du groupe sont rassemblées sous BNP Paribas ; le payload brut facultatif conserve l'organisation d'origine. Les dates de publication connues sont conservées. Les dates de début d'emploi et les deadlines ne sont pas inventées. Aucune absence dans cette recherche filtrée ne ferme une offre.

Plusieurs URLs peuvent partager le même identifiant BNP. Si les contenus métier sont identiques, une seule URL est choisie dans un ordre stable avant import. Si les contenus diffèrent, le scan est rejeté pour examen. Cela évite que deux alias alternent et créent de fausses modifications à chaque scan.

Les limites et options de recherche sont partagées avec Workday. Deux secondes séparent les requêtes au portail. La recherche `trading` est large et peut retourner des résultats liés à « trade » ; le filtre de titre restreint les détails. Cette couverture ne remplace pas tous les portails spécialisés BNP.

## Découverte suivante — UBS et Société Générale

- UBS : la page officielle de recherche mène à un portail BrassRing accessible, avec un site étudiants/graduates `5131`, partenaire `25008`. Ses scripts de recherche publics sont identifiés. Il reste à valider la session anonyme, les paramètres de recherche et les détails avant d'implémenter le connecteur. La simple accessibilité du HTML ne suffit pas à annoncer une collecte opérationnelle.
- Société Générale : portail et page de recherche accessibles. Les scripts publics indiquent un moteur Quantum et un échange OAuth. Aucun appel authentifié n'a été tenté. La redirection du répertoire d'offres a été examinée le 16 septembre : sa destination publique `/fr/Technical/toutes-les-offres` répond correctement et liste des offres françaises. La collecte des détails, la couverture anglaise et la déduplication des langues restent à implémenter et valider.

À l'issue du lot 4, ces deux sources étaient désactivées. UBS est activé dans le lot 5 ci-dessous et Société Générale dans le lot 6.

## Lot 5 — UBS étudiants/graduates

Le connecteur lit le tableau public lié par UBS, partenaire `25008`, site `5131`, lien étudiants/graduates `15232`. Il crée uniquement la session anonyme renvoyée par cette page, sans connexion candidat. Le contexte nécessaire à la recherche reste en mémoire et n'entre jamais dans les payloads d'offres ou les logs.

L'ensemble du tableau est parcouru, puis les titres Trading/Markets sont filtrés localement. Le paramètre de mot-clé n'est pas utilisé : la sonde a renvoyé le même tableau de 165 offres malgré ce paramètre. Les options `search_terms` sont donc refusées pour éviter de promettre un filtrage serveur inexistant.

La route publique de lecture `ProcessSortAndShowMoreJobs` est appelée avec le tri `LastUpdated`. Le serveur renvoie `PageSize=0` pour la taille par défaut ; le code de son interface confirme une pagination de 50. Un changement de total/taille, une page courte ou répétée fait échouer le scan. Les liens localisés contenant `frmSiteId=5131` sont acceptés, avec hôte, partenaire, route et identifiant de poste contrôlés.

Les détails proviennent des pages publiques `HomeWithPreLoad?PageType=JobDetails`. Toutes les rubriques de texte sont conservées, notamment missions et exigences. L'identifiant doit correspondre à la liste. Le champ `IsActive` des résultats de recherche n'est pas fiable pour déterminer l'ouverture : le connecteur vérifie `Jobdetails.isActive` dans la fiche. Une fiche explicitement inactive est écartée ; les données manquantes font échouer la collecte.

`lastupdated` n'est pas présenté comme une date de publication. Les deadlines UBS exprimées sans heure/fuseau ne sont pas converties en échéances précises dans ce lot. Elles restent dans le payload brut facultatif. Le tableau peut inclure plusieurs langues et des stages, ces derniers restant exclus de la priorité par le score commun. Le portail professionnel distinct et les postes sans les termes de titre sélectionnés ne sont pas couverts. L'inventaire reste partiel et ne sert pas à fermer des offres par absence.

Un total changeant, une page courte/répétée, une erreur GraphQL même avec HTTP 200, un refus robots/HTTP ou un budget dépassé empêchent l'import de la source. Deux secondes séparent les requêtes à chaque hôte. Le nombre d'offres varie ; les mesures d'import sont consignées dans VALIDATION-LOT3.md.

## Lot 6 — Société Générale

Le connecteur lit les répertoires publics français et anglais liés par le portail officiel, sans session candidat ni appel au moteur Quantum. Chaque répertoire doit contenir exactement le nombre de cartes annoncé. Références, routes, langues et doublons sont contrôlés ; une page tronquée ou un changement de format empêche l'import.

Les références communes aux deux langues sont réunies avant lecture des fiches, avec préférence stable pour l'anglais. Lors de la découverte du 16 septembre 2026 : 434 cartes françaises et 637 anglaises, dont 49 références communes, soit 1 022 références distinctes. Le filtre local de titres retient 33 offres. Il inclut les variantes françaises « structuration » et « salle des marchés » ainsi que « front office developer ».

Chaque fiche fournit son titre visible, ses sections de missions et de profil requis, ses lieux et son contrat. Le titre JSON-LD, qui ajoute parfois la division et le lieu, ne remplace pas le titre visible. Référence et URL canonique doivent correspondre au répertoire. La publication structurée est vérifiée contre la date affichée lorsqu'elle est présente. Le début d'emploi vient uniquement du libellé explicite ; « Immediately » reste un texte.

`validThrough` n'est pas utilisé comme deadline : sur les fiches inspectées, il correspondait au début d'emploi ou à une date déjà passée malgré la présence dans le répertoire. Aucune échéance n'est inventée. Le périmètre filtré reste partiel et ne permet pas de fermer une offre par absence.

Deux secondes séparent les requêtes au portail. Les limites de volume et de durée sont celles de `SearchOptions`, avec un maximum de 250 détails et 600 secondes. Les mots-clés de recherche serveur sont refusés, car la sélection est locale. Les imports et vérifications sont consignés dans [VALIDATION-LOT6.md](VALIDATION-LOT6.md).

## Lot 7 — Crédit Agricole CIB

Le [site carrière officiel](https://www.ca-cib.com/en/career) mène au tableau Talentsoft `jobs.ca-cib.com`. Le connecteur parcourt ses pages HTML publiques, avec `page` et `LCID=1036` : 100 cartes par page, dernière page ajustée au total. Chaque page doit afficher le même total et le bon numéro. Les références de carte doivent correspondre aux identifiants des URLs ; doublons et pages tronquées empêchent l'import. Le catalogue de 311 offres a été vérifié le 16 septembre 2026, puis filtré localement pour lire 24 fiches.

Les fiches conservent les champs de description et de critères candidat, pas seulement le résumé. Titre et référence sont vérifiés ; contrat, ville et zone géographique sont requis. La date explicitement nommée « Expected start date » est conservée lorsqu'elle existe. La date de mise à jour n'est pas présentée comme publication ; aucune deadline n'est inventée. Le minimum d'expérience est extrait uniquement du champ dédié et des formats de tranches vérifiés, dont `0-2 years`, `6 - 10 ans` et `11 ans et plus`. Un format inconnu reste inconnu, avec le texte original conservé.

Les contrats de type Stage ou Internship/Trainee sont exclus du classement prioritaire même si le titre ne mentionne pas de stage. Un contrat « Trainee » seul n'est pas exclu automatiquement. Les exigences structurées de plus de deux ans réduisent la compatibilité junior ; à partir de cinq ans elles déclenchent l'exclusion existante. Ces règles sont recalculables avec `rescore`.

## Lot 7 — HSBC étudiants/graduates

Le catalogue public « Find a programme » fournit le total, les paramètres de pagination et 20 premiers programmes. Les suivants sont lus via le GET public `/api/programmes/get-programmes`, conformément au script du site : `skip`, `take`, `count` et l'identifiant public de configuration `s`. Ce dernier vient de la page et n'est pas un secret. Les cartes promotionnelles ne font pas avancer `skip`. Les fragments inconnus, doublons et pages vides prématurées sont rejetés. Le catalogue est relu après pagination pour vérifier son total, ses paramètres et ses premiers résultats.

Les offres sélectionnées pointent vers les pages SuccessFactors publiques `/emergingtalent/job/.../{id}/`. Leur URL canonique peut changer de libellé mais doit garder l'identifiant. Le contenu métier complet, les critères d'éligibilité et tous les lieux sont conservés. Le lien de candidature est vérifié, sans être suivi. Le connecteur ne soumet aucune candidature.

Le début d'emploi vient du champ explicite « Start Date » de la carte. Publication et deadline proviennent des métadonnées des fiches, uniquement au format UTC explicite vérifié ; le code refuse une date ambiguë. La date d'ouverture de la carte et `datePosted` peuvent différer ; la date de la fiche est conservée. Les URLs de suivi des campagnes sont retirées. Les programmes Hang Seng sont regroupés sous HSBC. Les programmes de stage restent visibles en base, avec un score nul.

Couverture vérifiée : 75 programmes, 7 fiches Trading/Markets retenues. Le portail professionnel HSBC distinct n'est pas couvert. Les deux nouveaux connecteurs restent des recherches partielles, sans fermeture par absence. Ils utilisent les limites de volume et de durée communes, ainsi que le client HTTP avec vérification robots et espacement de deux secondes. Aucun watcher n'est démarré par leur activation. Bilan : [VALIDATION-LOT7.md](VALIDATION-LOT7.md).

## Lot 8 — Macquarie

Le portail public `recruitment.macquarie.com` utilise Avature. Le lien historique `www.careers.macquarie.com` n'a pas répondu lors de la découverte ; le portail de recrutement lié par le [site carrière officiel](https://www.macquarie.com/au/en/careers/graduates-and-interns.html) est accessible. Le connecteur utilise le formulaire de recherche en GET avec `search=trading`, `jobRecordsPerPage=9` et `jobOffset`. Le mot-clé affiché, le total, la page courante et le nombre de cartes sont vérifiés à chaque page. Les liens suivants du portail incorporent parfois le mot-clé dans le chemin : le connecteur reconstruit les paramètres explicites vérifiés au lieu de perdre le filtre.

La recherche du 16 septembre 2026 annonçait 87 résultats. Dix pages ont été parcourues, puis 17 titres Trading/Markets retenus. Les références sont réunies avant lecture des détails ; une répétition entre pages ou un contenu contradictoire entre recherches fait échouer la collecte.

Les fiches `JobDetail?jobId=...` doivent afficher le bon titre et le bon identifiant. Métadonnées et texte sont dans deux sections distinctes : elles sont toutes deux lues. Les rubriques « What role will you play? » et « What you offer » sont requises et non vides. Les lieux, le type de contrat et le niveau publié sont conservés. Le libellé générique « Date » n'est pas assimilé à une date de publication originale. Dates de début et deadlines restent inconnues faute de champ explicite vérifié.

Les niveaux publiés « Senior » ou « Mid-senior », sans niveau inférieur dans la même liste, excluent une offre de la priorité junior. « Junior » sert d'indice junior ; une combinaison uniquement « Mid-level » et « Senior » reste sans interprétation stricte. Une exigence d'expérience supérieure garde la priorité sur cet indice. Les tranches d'années sont extraites seulement de « What you offer », jamais de l'ancienneté du desk dans le texte institutionnel. Le poste « Operator Commodities Trading Associate » concerne les mouvements physiques, le transport, l'entreposage et la livraison de métaux ; son intitulé précis est exclu par les règles de score.

## Lot 8 — Nomura campus

Le [site Nomura Early Careers](https://www.nomura.com/careers/early-careers/apply-to-nomura/) lie le tableau Oleeo des offres `vacancy/1`. Le tableau d'événements `vacancy/2` est hors périmètre. Les 44 résultats observés sont présents dans une table unique. Le connecteur vérifie le total annoncé, les colonnes, les références et les doublons ; si une pagination future tronque cette table, le scan échoue au lieu d'importer silencieusement une page partielle.

Les titres sont filtrés localement avant lecture des fiches. Les liens du tableau contiennent un préfixe de contexte `vx/.../xf-...` ; la route publique sans ce préfixe a été vérifiée et sert d'URL stable. Référence et titre sont contrôlés contre la fiche. L'action du formulaire de candidature est lue pour confirmer l'identifiant, mais jamais appelée. Les champs de formulaire anti-CSRF ne sont ni stockés ni utilisés.

Division, lieu, type de programme et description intégrale sont conservés. La colonne de deadline n'indique aucun fuseau : aucune échéance précise n'en est déduite. Les dates présentes dans le texte restent lisibles dans la description ; aucune date de publication ou de début d'emploi n'est inventée. Les 12 offres retenues lors de la validation sont des stages, y compris les « Graduate Internship » ; elles sont stockées mais exclues du classement prioritaire.

Le portail professionnel [careers.nomura.com](https://careers.nomura.com/Nomura?locale=en_US) a été identifié comme une source distincte ; il n'est pas couvert dans ce lot. Macquarie et Nomura campus restent des collectes filtrées, sans fermeture d'une offre déduite de son absence. Les limites, la politique robots et l'espacement HTTP sont communs au projet. Bilan : [VALIDATION-LOT8.md](VALIDATION-LOT8.md).

## Lot 9 — Optiver

Le [portail officiel Optiver](https://www.optiver.com/join-us/jobs) expose l'API publique `/en/api/v1/jobs`. Les paramètres `from` et `size=16` ont été vérifiés dans le code du bouton « Load more », puis par une lecture réelle de la deuxième page. Le connecteur parcourt les 165 cartes observées, sans filtre serveur, puis sélectionne les titres Trading/Markets localement. Le total, la taille des pages, les identifiants de cartes et les URLs doivent être cohérents. Une nouvelle lecture de la première page détecte un changement d'ordre ou de total pendant la pagination. Ce contrôle ne constitue pas une garantie transactionnelle du catalogue distant.

Les fiches doivent concorder sur le titre, l'URL canonique, le lieu, le département et le niveau. L'identifiant `meta jobid` sert d'identité stable, distinct de l'identifiant interne de carte. La description est prise uniquement dans `rich-text-section`, sans les recommandations de postes et le pied de page. Aucun formulaire de candidature n'est suivi. Les niveaux Graduate/Early Careers apportent un indice junior ; Experienced ne signifie pas automatiquement Senior. Internship est conservé comme contrat et exclu de la priorité. Les dates de publication sans heure/fuseau et dates du texte ne sont pas transformées en instants UTC ou en début d'emploi supposé.

Deux cas ont été vérifiés dans leurs descriptions : [Career Kickstarter](https://www.optiver.com/join-us/jobs/institutional-sales-and-trading/amsterdam/career-kickstarter-trading-2026/) est un programme de découverte de cinq jours pouvant déboucher sur une offre ; [Expressions of Interest](https://www.optiver.com/join-us/jobs/institutional-sales-and-trading/sydney/expressions-of-interest-graduate-quantitative-trader-2027/) précise que les candidatures formelles sont fermées et propose une inscription au vivier. Ils restent consultables avec score nul. L'événement [The Trading Floor](https://www.optiver.com/join-us/jobs/institutional-sales-and-trading/amsterdam/institutional-trader-3/) est exclu du filtre de titres. Aucun de ces cas n'est présenté comme un poste graduate ouvert confirmé.

Les 27 fiches sélectionnées constituent une couverture filtrée : `complete=False`, donc aucune fermeture par absence. Limites de durée, de volume et de détails, robots et espacement des requêtes restent actifs. Bilan dans [VALIDATION-LOT9.md](VALIDATION-LOT9.md).

## Lot 9 — Citadel Securities, désactivé

Le [répertoire officiel](https://www.citadelsecurities.com/careers/open-opportunities/) présente des offres par expérience, métier et localisation. La lecture HTTP par le client du projet a reçu **403 le 16 septembre 2026**. La visibilité dans un moteur de recherche ne valide pas un connecteur automatisé. Source configurée mais désactivée ; aucun adaptateur n'a été implémenté et aucune offre importée. Une reprise demandera une validation complète du catalogue et des fiches, notamment pour distinguer postes ouverts et expressions d'intérêt.

## Lot 10 — IMC et DRW

Le détail [IMC Quantitative Trader Intern](https://www.imc.com/us/careers/jobs/4823923101) expose la même référence et le lien `job-boards.eu.greenhouse.io/imc/jobs/4823923101`. Le détail [DRW Quantitative Trading Analyst](https://www.drw.com/work-at-drw/listings/quantitative-trading-analyst-3445781) lie explicitement `job-boards.greenhouse.io/drweng/jobs/7929846` : l'identifiant interne du site DRW diffère de celui du post Greenhouse. Le collecteur conserve ce dernier, stable dans le tableau public.

Les deux flux utilisent **`boards-api.greenhouse.io`**, même pour IMC dont les candidatures sont hébergées en Europe. L'hôte européen supposé `boards-api.eu.greenhouse.io` a échoué en transport et n'est pas utilisé. Les GET publics `/v1/boards/imc/jobs?content=true` et `/v1/boards/drweng/jobs?content=true` ont renvoyé respectivement 174 et 153 annonces le 16 septembre 2026. D'après la [documentation Greenhouse Job Board](https://docs.greenhouse.io/job-board.html), cette route fournit tous les posts et `content=true` ajoute les descriptions. Le total `meta.total` doit correspondre exactement au nombre de lignes ; aucune pagination arbitraire n'est ajoutée.

Le nouveau connecteur `greenhouse_filtered` contrôle tous les identifiants, doublons, noms d'employeur et URLs, puis filtre les titres localement. Les posts dont `internal_job_id` est nul sont des inscriptions en vivier selon le contrat Greenhouse ; ils sont ignorés. IMC expose aussi `Is Hidden Job?` : une valeur vraie exclut le post. Les dates `first_published` et `application_deadline` sont lues uniquement comme horodatages valides avec fuseau ; `updated_at` ne devient jamais une date de publication.

Pour IMC, `Worker Sub Type` distingue Graduate, Experienced, Intern, Working Student et Temporary. Graduate apporte un indice junior, Intern un contrat de stage. Les textes de début d'emploi sont extraits uniquement après des formulations explicites de début ou d'emploi à temps plein ; les dates de nouvelle candidature ne servent pas de prise de poste. Pour DRW, `Employment Type` et `Target Start Date` sont conservés tels que publiés : « Summer 2027 » reste une saison, « Immediate » n'est pas transformé en date calendaire. Le tableau français DRW n'est pas collecté.

Les descriptions intégrales de 26 posts par employeur ont été importées. Les titres Recruiter, Administrative Assistant, Working Student et Trading Application Specialist restent consultables avec score nul : recrutement, assistance administrative, emploi étudiant à temps partiel et gestion des applications/fournisseurs sont hors de la cible. Les autres postes Experienced ne sont pas artificiellement transformés en Senior. Le périmètre filtré renvoie toujours `complete=False` et n'infère aucune fermeture par absence. Le connecteur Greenhouse historique de Jane Street est conservé. Bilan : [VALIDATION-LOT10.md](VALIDATION-LOT10.md).

## Lot 11 — SIG / Susquehanna

Le [site institutionnel](https://sig.com/careers/) lie `careers.sig.com/jobs`. Ce portail expose le catalogue public `/api/jobs?page=1&limit=100`. Les premières, deuxièmes et dernières pages ont été vérifiées : 265 références distinctes en trois pages de 100, 100 et 65 résultats. Le client du projet a également vérifié la fiche [Quantitative Trader — Graduate 2027 à Londres](https://careers.sig.com/jobs/11031?lang=en-us), dont l'identité, la description, la publication et le contrat correspondent aux données publiques. Le fichier JavaScript d'un CDN technique a refusé la lecture (403), tandis que le portail et son catalogue public sont accessibles ; aucun contournement n'a été utilisé.

Chaque page contient descriptions et qualifications. Le collecteur vérifie leur présence et ajoute les qualifications à la description lorsqu'elles n'y figurent pas déjà. Identifiants, employeur, langue, visibilité, totaux et taille des pages sont contrôlés. Une nouvelle lecture de la première page détecte une modification du contenu ou du total pendant la pagination ; cela ne garantit pas un instantané transactionnel du serveur. Les liens vers la connexion candidat sont validés pour leur référence mais jamais suivis : l'URL conservée ouvre la fiche publique.

Les titres sont filtrés après le catalogue complet. Student Discovery Program, postes non consultables/candidatables publiquement, Operations et Sports Analytics sont exclus du périmètre. Les deux Trading Desk Associate inspectés sont classés Operations par SIG et décrivent rapprochements, suivi de positions et processus opérationnels. `New Graduates` apporte un indice junior. `Interns + Co-ops` impose un contrat de stage ; un contrat explicite `INTERN` garde aussi priorité sur un titre graduate. Dix fiches collectées présentent cette contradiction New Graduates/INTERN et ont donc score nul. Cette prudence peut exclure des postes diplômés réellement ouverts ; leur qualification doit être vérifiée auprès de la source avant correction.

`tags3` conserve le mois cible ou Immediate/Flexible Start, sans inventer un jour. `posted_date` sert de publication ; `validThrough`, observé comme échéance technique annuelle sur la fiche inspectée, n'est pas assimilé à une deadline candidat. Bilan dans [VALIDATION-LOT11.md](VALIDATION-LOT11.md).

## Lot 11 — Flow Traders

Le [client de recherche officiel](https://www.flowtraders.com/js/job-search.js) utilise le tableau Greenhouse `flowtraders`, via `boards-api.greenhouse.io`. Les 41 posts publics et leurs descriptions sont lus en une réponse ; le total est vérifié par le connecteur partagé. La métadonnée Division distingue les événements : Flow Quant Trading Days et le vivier Trading Systems Engineer appartiennent à Events et sont exclus.

Les dix fiches retenues gardent la métadonnée Start Date si elle est une date ISO valide ; vide ou nulle, elle reste inconnue. La date n'est pas utilisée pour déduire une deadline ou fermer l'annonce. New York publie le 30 août 2027 dans ses métadonnées et « Fall 2027 » dans le texte ; Amsterdam conserve le 1er juin 2026 malgré une description de candidature ouverte toute l'année ; Hong Kong ne fournit pas de date. Ces limites restent visibles dans le bilan et les descriptions. Les métadonnées de contacts ne sont pas reprises dans le payload brut conservable du connecteur.

Les deux sources restent filtrées (`complete=False`), sans fermeture par absence. Les limites de temps et de volume, robots et espacement HTTP communs s'appliquent. Les sources existantes n'ont pas été rescannées pendant ce lot.

## Mesure Citi complémentaire — lot 30

Les facettes publiques Workday peuvent être transmises explicitement par la sonde
sans modifier les sources configurées. Les quatre recherches `repo` / `securities finance`
dans `Institutional Trading` / `Management Development Programs` ont été paginées
le 17 septembre 2026 ; elles retiennent 26 chemins distincts, tous déjà connus.
Aucun détail connu n'a été relu et aucune offre n'a été importée. Le périmètre actif
reste `trading` sans facette. Voir [la mesure et ses limites](CITI-FACET-SCOPE-LOT30.md).

## Lot 3 — Oracle / JPMorgan, désactivé

Le portail JPMorgan et la tentative de recherche publique ont renvoyé HTTP 403 depuis cet environnement. Aucun contournement n'a été tenté. Le connecteur est donc disponible dans le code, avec des tests synthétiques, mais JPMorgan n'est pas une source surveillée actuellement.

Le contrat préparé utilise exclusivement les ressources Candidate Experience `recruitingCEJobRequisitions` et `recruitingCEJobRequisitionDetails`. Les paramètres de pagination `limit` et `offset` appartiennent au `finder=findReqs;siteNumber=...,limit=25,offset=...,keyword=...`. Une page plus petite que 25 avance selon le nombre réellement reçu ; une page vide avant le total, répétée ou incohérente fait échouer le scan. Les descriptions, responsabilités et qualifications sont réunies, même si un résumé court est fourni. L'identifiant du détail est vérifié. `PostedDate` sert à la publication ; les dates absentes restent inconnues.

La configuration accepte seulement une racine publique Oracle Candidate Experience et refuse les paramètres de recherche contenant des séparateurs de finder. Avant toute activation, une collecte réseau réussie doit confirmer le schéma exact du tenant JPMorgan, les détails et les liens. Les options de recherche et les protections d'import sont celles des autres recherches partielles.
