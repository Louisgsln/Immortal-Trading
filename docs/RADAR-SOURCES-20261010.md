# Sources du radar — relevé OVH du 10 octobre 2026

Relevé : `2026-10-10T18:41:43.909960+00:00` (UTC). **75 sources activées, 65 employeurs,
74 adresses de catalogue distinctes : 73 sources à jour, une partielle et une ancienne.**
Radar actif ; seuil des alertes 70/100 ; off-cycle et stages longs 2027 inclus,
Summer hors alertes. [Validation](VALIDATION-LOTS132-138-139.md),
[audit des accès manquants](CAMPUS-FUNDS-AUDIT-20261010.md) et [carnet](TASK-BOARD.md).

`/statuts`, `/statut` et `/status` affichent le même nombre de sources activées,
le nombre à jour et les employeurs distincts. `/sources`, `/sources 2` et
`/sources 3` donnent l'inventaire complet dans le chat privé. La fraîcheur évolue
au fil des collectes ; ce fichier est un relevé daté, le bot et le Dashboard sont actualisés.

Une source est un périmètre de collecte, parfois campus/professionnels distincts.
Citi et Citi campus partagent la même adresse avec des recherches différentes :
ils comptent comme deux sources, une adresse et un employeur. Les offres sont
dédupliquées par identité et reliées aux sources via `job_sources`.

Les fiches ci-dessous sont celles du dernier catalogue cohérent retenu par les
filtres métiers, avant seuil et politique de stage. Elles ne sont ni toutes les
offres de l'entreprise, ni des offres publiées aujourd'hui. Une source à jour
avec zéro fiche signifie zéro résultat dans ce périmètre. Les recherches Workday
restent ciblées ; une couverture mondiale exhaustive n'est pas prouvée.

Optiver est partiel : une fiche Trading Automation Specialist reste invérifiable.
BNP Paribas est ancien : dernier succès en septembre, accès français refusé en 403.
Les anciennes fiches sont conservées ; ces deux sources ne sont pas déclarées à jour.
Nomura campus a repris ses collectes publiques ; l'intervention humaine reste en
attente si le CAPTCHA revient. JPMorgan campus, NatWest, Citadel et Two Sigma,
ainsi que les connecteurs non encore validés, ne sont pas ajoutés aux 75.

| Nº | Employeur | Source | Catalogue public | État | Dernier succès UTC | Fiches |
|---:|---|---|---|---|---|---:|
| 1 | 3Red Partners | `3red` | [Portail](https://job-boards.greenhouse.io/3redpartners) | À jour | 2026-10-10 18:41:17 | 3 |
| 2 | Acadian Asset Management | `acadian` | [Portail](https://www.acadian-asset.com/careers/open-positions) | À jour | 2026-10-10 18:05:57 | 0 |
| 3 | Akuna Capital | `akuna_capital` | [Portail](https://akunacapital.com/careers/) | À jour | 2026-10-10 18:41:27 | 10 |
| 4 | AQR | `aqr` | [Portail](https://careers.aqr.com/) | À jour | 2026-10-10 18:07:12 | 3 |
| 5 | Aquatic Capital Management | `aquatic` | [Portail](https://job-boards.greenhouse.io/aquaticcapitalmanagement) | À jour | 2026-10-10 18:08:09 | 4 |
| 6 | Bank of America | `bank_of_america` | [Portail](https://ghr.wd1.myworkdayjobs.com/lateral-us) | À jour | 2026-10-10 18:21:22 | 11 |
| 7 | Bank of America | `bank_of_america_campus` | [Portail](https://careers.bankofamerica.com/en-us/students/job-search) | À jour | 2026-10-10 18:12:00 | 10 |
| 8 | Barclays | `barclays` | [Portail](https://barclays.wd3.myworkdayjobs.com/External_Career_Site_Barclays) | À jour | 2026-10-10 18:38:13 | 23 |
| 9 | BNP Paribas | `bnp_paribas` | [Portail](https://group.bnpparibas/emploi-carriere/toutes-offres-emploi) | Ancienne | 2026-09-16 19:06:21 | 23 |
| 10 | Capula | `capula` | [Portail](https://apply.workable.com/capula-investment-management-ltd/) | À jour | 2026-10-10 18:39:02 | 3 |
| 11 | Chicago Trading Company | `chicago_trading` | [Portail](https://www.chicagotrading.com/search) | À jour | 2026-10-10 18:30:59 | 3 |
| 12 | Chicago Trading Company | `chicago_trading_campus` | [Portail](https://www.chicagotrading.com/campus) | À jour | 2026-10-10 18:31:19 | 5 |
| 13 | Citi | `citi` | [Portail](https://citi.wd5.myworkdayjobs.com/2) | À jour | 2026-10-10 18:29:51 | 42 |
| 14 | Citi | `citi_campus` | [Portail](https://citi.wd5.myworkdayjobs.com/2) | À jour | 2026-10-10 18:40:06 | 17 |
| 15 | Crédit Agricole CIB | `credit_agricole_cib` | [Portail](https://jobs.ca-cib.com/pages/offre/listeoffre.aspx) | À jour | 2026-10-10 18:40:57 | 27 |
| 16 | Da Vinci | `da_vinci` | [Portail](https://davincitrading.com/careers/) | À jour | 2026-10-10 18:11:22 | 10 |
| 17 | Deutsche Bank | `deutsche_bank` | [Portail](https://db.wd3.myworkdayjobs.com/DBWebsite) | À jour | 2026-10-10 18:32:45 | 21 |
| 18 | Deutsche Bank | `deutsche_bank_campus` | [Portail](https://careers.db.com/students-graduates/search-programmes/index?language_id=1) | À jour | 2026-10-10 18:39:37 | 22 |
| 19 | DRW | `drw` | [Portail](https://www.drw.com/work-at-drw/listings) | À jour | 2026-10-10 18:35:16 | 29 |
| 20 | DV Trading | `dv_trading` | [Portail](https://dvtrading.co/join-dv/) | À jour | 2026-10-10 18:32:29 | 21 |
| 21 | Engineers Gate | `engineers_gate` | [Portail](https://www.eglp.com/) | À jour | 2026-10-10 18:13:13 | 4 |
| 22 | Five Rings | `five_rings` | [Portail](https://fiverings.com/careers/) | À jour | 2026-10-10 18:32:51 | 5 |
| 23 | Flow Traders | `flow_traders` | [Portail](https://www.flowtraders.com/careers/job-search/) | À jour | 2026-10-10 18:41:04 | 11 |
| 24 | Gelber Group | `gelber` | [Portail](https://www.gelbergroup.com/careers/) | À jour | 2026-10-10 18:13:18 | 10 |
| 25 | Geneva Trading | `geneva_trading` | [Portail](https://www.genevatrading.com/careers-open-positions/) | À jour | 2026-10-10 18:13:33 | 5 |
| 26 | Goldman Sachs | `goldman_campus` | [Portail](https://higher.gs.com/campus) | À jour | 2026-10-10 18:31:47 | 17 |
| 27 | Goldman Sachs | `goldman_sachs` | [Portail](https://higher.gs.com/results) | À jour | 2026-10-10 18:35:38 | 37 |
| 28 | Graham Capital Management | `graham` | [Portail](https://www.grahamcapital.com/careers/) | À jour | 2026-10-10 18:13:38 | 1 |
| 29 | Graviton Research Capital | `graviton` | [Portail](https://job-boards.greenhouse.io/gravitonresearchcapital) | À jour | 2026-10-10 18:15:25 | 7 |
| 30 | Headlands Technologies | `headlands` | [Portail](https://www.headlandstech.com/careers/) | À jour | 2026-10-10 18:17:35 | 2 |
| 31 | HSBC | `hsbc_graduates` | [Portail](https://www.hsbc.com/careers/students-and-graduates/find-a-programme) | À jour | 2026-10-10 18:30:31 | 8 |
| 32 | HSBC | `hsbc_professionals` | [Portail](https://portal.careers.hsbc.com/careers) | À jour | 2026-10-10 18:34:19 | 4 |
| 33 | Hudson River Trading | `hudson_river_trading` | [Portail](https://www.hudsonrivertrading.com/careers/) | À jour | 2026-10-10 18:33:02 | 10 |
| 34 | IMC | `imc` | [Portail](https://www.imc.com/us/search-careers) | À jour | 2026-10-10 18:40:40 | 28 |
| 35 | ING | `ing` | [Portail](https://ing.wd3.myworkdayjobs.com/ICSGBLCOR) | À jour | 2026-10-10 18:13:27 | 6 |
| 36 | Jane Street | `jane_street` | [Portail](https://www.janestreet.com/join-jane-street/open-roles/) | À jour | 2026-10-10 18:40:23 | 231 |
| 37 | Jefferies | `jefferies_campus` | [Portail](https://jefferies.tal.net/vx/lang-en-GB/mobile-0/appcentre-ext/brand-4/candidate/jobboard/vacancy/2/adv/) | À jour | 2026-10-10 18:14:42 | 3 |
| 38 | Jump Trading | `jump_trading` | [Portail](https://www.jumptrading.com/careers) | À jour | 2026-10-10 18:40:29 | 25 |
| 39 | Lazard | `lazard_campus` | [Portail](https://icbpjb.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2) | À jour | 2026-10-10 18:39:13 | 4 |
| 40 | Macquarie | `macquarie` | [Portail](https://recruitment.macquarie.com/en_US/careers/SearchJobs/) | À jour | 2026-10-10 18:30:46 | 12 |
| 41 | Mako | `mako` | [Portail](https://www.mako.com/opportunities) | À jour | 2026-10-10 18:19:34 | 3 |
| 42 | Man Group | `man_group` | [Portail](https://www.man.com/careers) | À jour | 2026-10-10 18:19:25 | 8 |
| 43 | Marshall Wace | `marshall_wace_graduates` | [Portail](https://www.mwam.com/join-us/early-careers/) | À jour | 2026-10-10 18:18:32 | 1 |
| 44 | Maven Securities | `maven_securities` | [Portail](https://www.mavensecurities.com/jobs/) | À jour | 2026-10-10 18:33:09 | 10 |
| 45 | Millennium | `millennium_campus` | [Portail](https://campusjobs.mlp.com/careers?domain=mlp.com&microsite=campus-site) | À jour | 2026-10-10 18:40:16 | 18 |
| 46 | Morgan Stanley | `morgan_stanley` | [Portail](https://ms.wd5.myworkdayjobs.com/External) | À jour | 2026-10-10 18:33:06 | 14 |
| 47 | Morgan Stanley | `morgan_stanley_campus` | [Portail](https://morganstanley.tal.net/vx/lang-en-GB/candidate/jobboard/vacancy/1/adv) | À jour | 2026-10-10 18:33:44 | 18 |
| 48 | Nomura | `nomura_campus` | [Portail](https://nomuracampus.tal.net/vx/lang-en-GB/mobile-0/appcentre-ext/brand-4/xf-3348347fc789/candidate/jobboard/vacancy/1/adv/) | À jour | 2026-10-10 18:41:01 | 8 |
| 49 | Nomura | `nomura_professionals` | [Portail](https://careers.nomura.com/Nomura?locale=en_US) | À jour | 2026-10-10 18:31:13 | 16 |
| 50 | Old Mission | `old_mission` | [Portail](https://www.oldmissioncapital.com/careers/) | À jour | 2026-10-10 18:33:17 | 20 |
| 51 | Optiver | `optiver` | [Portail](https://www.optiver.com/join-us/jobs) | Partielle | 2026-10-10 18:35:05 | 24 |
| 52 | PDT Partners | `pdt` | [Portail](https://pdtpartners.com/careers) | À jour | 2026-10-10 18:20:46 | 2 |
| 53 | Point72 | `point72` | [Portail](https://careers.point72.com/) | À jour | 2026-10-10 18:33:21 | 31 |
| 54 | Quantbot Technologies | `quantbot` | [Portail](https://www.quantbot.com/careers/) | À jour | 2026-10-10 18:20:51 | 5 |
| 55 | Qube Research & Technologies | `qube_research` | [Portail](https://job-boards.greenhouse.io/quberesearchandtechnologies) | À jour | 2026-10-10 18:23:17 | 23 |
| 56 | Radix Trading | `radix_campus` | [Portail](https://job-boards.greenhouse.io/radixuniversity) | À jour | 2026-10-10 18:23:42 | 2 |
| 57 | Radix Trading | `radix_professionals` | [Portail](https://job-boards.greenhouse.io/radixexperienced) | À jour | 2026-10-10 18:23:51 | 1 |
| 58 | RBC | `rbc` | [Portail](https://rbc.wd3.myworkdayjobs.com/RBCGLOBAL1) | À jour | 2026-10-10 18:09:11 | 11 |
| 59 | Santander | `santander` | [Portail](https://santander.wd3.myworkdayjobs.com/SantanderCareers) | À jour | 2026-10-10 18:23:05 | 11 |
| 60 | Schonfeld | `schonfeld` | [Portail](https://www.schonfeld.com/careers/) | À jour | 2026-10-10 18:33:29 | 11 |
| 61 | Société Générale | `societe_generale` | [Portail](https://careers.societegenerale.com/fr/Technical/toutes-les-offres) | À jour | 2026-10-10 18:34:50 | 34 |
| 62 | Squarepoint Capital | `squarepoint_capital` | [Portail](https://www.squarepoint-capital.com/open-opportunities) | À jour | 2026-10-10 18:33:34 | 15 |
| 63 | Susquehanna | `sig` | [Portail](https://careers.sig.com/jobs) | À jour | 2026-10-10 18:32:56 | 51 |
| 64 | Tower Research Capital | `tower_research` | [Portail](https://tower-research.com/roles/) | À jour | 2026-10-10 18:34:25 | 22 |
| 65 | TransMarket Group | `transmarket_group` | [Portail](https://www.transmarketgroup.com/careers) | À jour | 2026-10-10 18:34:56 | 4 |
| 66 | Tudor Group | `tudor` | [Portail](https://job-boards.greenhouse.io/tudorgroup) | À jour | 2026-10-10 18:24:04 | 2 |
| 67 | UBS | `ubs` | [Portail](https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5131&PageType=searchResults&SearchType=linkquery&LinkID=15232) | À jour | 2026-10-10 18:33:24 | 4 |
| 68 | UBS | `ubs_professionals` | [Portail](https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=searchResults&SearchType=linkquery&LinkID=15231) | À jour | 2026-10-10 18:32:22 | 31 |
| 69 | Verition | `verition` | [Portail](https://www.verition.com/open-positions) | À jour | 2026-10-10 18:24:36 | 4 |
| 70 | Virtu Financial | `virtu_financial` | [Portail](https://www.virtu.com/careers/) | À jour | 2026-10-10 18:35:02 | 21 |
| 71 | Walleye Capital | `walleye_capital` | [Portail](https://walleyecapital.com/careers) | À jour | 2026-10-10 18:35:11 | 3 |
| 72 | Wells Fargo | `wells_fargo` | [Portail](https://wf.wd1.myworkdayjobs.com/WellsFargoJobs) | À jour | 2026-10-10 18:12:48 | 2 |
| 73 | Winton | `winton` | [Portail](https://job-boards.eu.greenhouse.io/winton) | À jour | 2026-10-10 18:24:41 | 1 |
| 74 | WorldQuant | `worldquant` | [Portail](https://job-boards.greenhouse.io/worldquant) | À jour | 2026-10-10 18:25:10 | 15 |
| 75 | XTX Markets | `xtx_markets` | [Portail](https://www.xtxmarkets.com/careers/) | À jour | 2026-10-10 18:40:34 | 1 |

## Ajouts vérifiés de cette livraison

| Source | Fiches au premier succès | Score ≥70 | Stages off-cycle/longs 2027 ≥70 |
|---|---:|---:|---:|
| `citi_campus` | 17 | 6 | 1 |
| `deutsche_bank_campus` | 22 | 4 | 0 |
| `lazard_campus` | 4 | 0 | 0 |
| `millennium_campus` | 18 | 1 | 0 |
| `capula` | 3 | 0 | 0 |

Ces colonnes comptent les associations à chaque source, y compris les offres déjà
présentes via Citi professionnels. Elles ne prédisent pas les alertes envoyées et
ne prouvent pas l'éligibilité personnelle. Les premiers imports sont silencieux.
La dernière colonne exige un stage confirmé au bon format et millésime ; elle
exclut les graduate, postes professionnels et formats inconnus. Le témoin Citi
Sales and Trading off-cycle Paris est à 100/100, six mois dès janvier 2027.
Millennium comprend un véritable off-cycle Hong Kong de 3–6 mois en 2026 : détecté,
mais hors millésime 2027. Capula écarte la candidature quantitativement intéressante
explicitement spéculative. Barclays élargi est une source existante, pas une sixième
nouvelle source ; dernier catalogue : 23 fiches.
