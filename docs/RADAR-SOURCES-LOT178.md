# Sources supplémentaires — lot 178 préparé

Deux contrôles publics concordants du 19 octobre 2026 depuis le VPS. Six employeurs supplémentaires
ont une collecte complète dans leur périmètre et des fiches validées ; ils ne sont
pas encore installés. Le profil préparé compte **128 sources / 116 employeurs**,
contre **122 / 110 en exploitation**. Les compteurs du bot restent ceux du profil
effectivement installé.

| Source | Employeur | Catalogue | Offres retenues |
|---|---|---|---:|
| lloyds | Lloyds Banking Group | https://lbg.wd3.myworkdayjobs.com/LBG_Careers | 4 |
| lombard_odier | Lombard Odier | https://lombardodier.wd3.myworkdayjobs.com/Lombard_Odier_Careers | 4 |
| janus_henderson | Janus Henderson | https://jobs.janushenderson.com/ | 4 |
| belvedere | Belvedere Trading | https://jobs.lever.co/belvederetrading | 7 |
| tibra | Tibra Capital | https://apply.workable.com/tibra-capital-1/ | 0 |
| eclipse | Eclipse Trading | https://www.eclipsetrading.com/all-jobs/ | 8 |

167 résultats examinés, dédupliqués par source ; 27 fiches retenues, dont dix à score
≥ 70 et dix-sept à zéro. Les deux inventaires et les champs des fiches sont identiques.
[Preuves avec empreintes et échantillons](SOURCE-AUDIT-LOT178.json). Un score élevé ne
confirme pas les critères d’un stage, une date de début ou l’éligibilité du candidat.

Provenance : pages Careers Lloyds et Lombard Odier ; site corporate Janus Henderson ;
page New Graduates/Campus Recruiting de Belvedere ; page Careers Tibra ; module
Greenhouse publié sur la page All Jobs d’Eclipse. Ces liens établissent l’origine
des catalogues, sans prétendre couvrir tous les portails campus d’un groupe.

Belvedere publie notamment une offre Winter Quarter 2027 : sa présence dans le
catalogue ne la transforme pas automatiquement en stage off-cycle admissible.
Tibra déclare un catalogue vide, avec contrôle du guide public et de la liste.
Les critères off-cycle/longs 2027 restent distincts du flux Telegram de tous scores.
Les dates ou durées absentes restent inconnues ; aucun bonus de score par employeur.

Voleon publie un module Ashby mais son API répond HTTP 401 : non activé. Les accès
Julius Baer et Schroders répondent HTTP 403 ; Rokos, Balyasny et Aspect demandent
encore un adaptateur validé. Aucun n’est ajouté au compteur. LinkedIn est un
[import manuel distinct](LINKEDIN.md), sans collecte H24 ni nouvel employeur comptabilisé.

[Validation](VALIDATION-LOTS177-179.md) · [Carnet](TASK-BOARD.md).

## Inventaire installé — contrôle du 19 octobre

Relevé à **17:26 UTC : 122 sources / 110 employeurs, 110 à jour**, radar actif,
alertes de toutes les nouvelles offres activées, même à zéro. [Inventaire daté](RADAR-INVENTORY-20261019.json).
Les six ajouts de la première table restent hors exploitation ; aucun import LinkedIn manuel
n’est compté comme un portail surveillé. Le nombre de sources et le nombre de fiches sont distincts.

| Source | Employeur | Portail | État au relevé |
|---|---|---|---|
| 3red | 3Red Partners | https://job-boards.greenhouse.io/3redpartners | À jour |
| aberdeen | Aberdeen | https://abrdn.wd3.myworkdayjobs.com/abrdn | À jour |
| acadian | Acadian Asset Management | https://www.acadian-asset.com/careers/open-positions | À jour |
| akuna_capital | Akuna Capital | https://akunacapital.com/careers/ | À jour |
| alliancebernstein | AllianceBernstein | https://abglobal.wd1.myworkdayjobs.com/alliancebernsteincareers | À jour |
| aqr | AQR | https://careers.aqr.com/ | À jour |
| aquatic | Aquatic Capital Management | https://job-boards.greenhouse.io/aquaticcapitalmanagement | À jour |
| arrowstreet | Arrowstreet Capital | https://arrowstreetcapital.wd5.myworkdayjobs.com/Arrowstreet | À jour |
| bank_of_america | Bank of America | https://ghr.wd1.myworkdayjobs.com/lateral-us | À jour |
| bank_of_america_campus | Bank of America | https://careers.bankofamerica.com/en-us/students/job-search | À jour |
| barclays | Barclays | https://barclays.wd3.myworkdayjobs.com/External_Career_Site_Barclays | À jour |
| blackrock | BlackRock | https://blackrock.wd1.myworkdayjobs.com/BlackRock_Professional | À jour |
| bluecrest | BlueCrest Capital Management | https://job-boards.greenhouse.io/bluecrestcapitalmanagement | À jour |
| bmo | BMO | https://bmo.wd3.myworkdayjobs.com/External | À jour |
| bnp_campus | BNP Paribas | https://group.bnpparibas/en/careers/all-job-offers/trainee-internship | Échec récent |
| bnp_paribas | BNP Paribas | https://group.bnpparibas/emploi-carriere/toutes-offres-emploi | Collecte ancienne |
| bp | BP | https://bpinternational.wd3.myworkdayjobs.com/bpCareers | À jour |
| brevan_howard | Brevan Howard | https://brevanhoward.wd3.myworkdayjobs.com/BH_ExternalCareers | À jour |
| bridgewater | Bridgewater Associates | https://job-boards.greenhouse.io/bridgewater89 | À jour |
| cfm | Capital Fund Management | https://jobs.cfm.com/ | À jour |
| capula | Capula | https://apply.workable.com/capula-investment-management-ltd/ | À jour |
| caxton | Caxton Associates | https://apply.workable.com/caxton/ | À jour |
| chicago_trading | Chicago Trading Company | https://www.chicagotrading.com/search | À jour |
| chicago_trading_campus | Chicago Trading Company | https://www.chicagotrading.com/campus | À jour |
| cibc | CIBC | https://cibc.wd3.myworkdayjobs.com/search | À jour |
| citi | Citi | https://citi.wd5.myworkdayjobs.com/2 | Échec récent |
| citi_campus | Citi | https://citi.wd5.myworkdayjobs.com/2 | À jour |
| credit_agricole_cib | Crédit Agricole CIB | https://jobs.ca-cib.com/pages/offre/listeoffre.aspx | À jour |
| deshaw | D. E. Shaw | https://www.deshaw.com/careers | À jour |
| da_vinci | Da Vinci | https://davincitrading.com/careers/ | À jour |
| danske | Danske Bank | https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001 | À jour |
| deutsche_bank | Deutsche Bank | https://db.wd3.myworkdayjobs.com/DBWebsite | À jour |
| deutsche_bank_campus | Deutsche Bank | https://careers.db.com/students-graduates/search-programmes/index?language_id=1 | À jour |
| dimensional | Dimensional Fund Advisors | https://dimensional.wd5.myworkdayjobs.com/DFA_Careers | À jour |
| drw | DRW | https://www.drw.com/work-at-drw/listings | À jour |
| dv_trading | DV Trading | https://dvtrading.co/join-dv/ | À jour |
| dymon_asia | Dymon Asia | https://job-boards.anz.greenhouse.io/dymonasiacapitalsingaporepteltd | À jour |
| engineers_gate | Engineers Gate | https://www.eglp.com/ | À jour |
| farallon | Farallon Capital Management | https://job-boards.greenhouse.io/faralloncapitalmanagementllc | À jour |
| five_rings | Five Rings | https://fiverings.com/careers/ | À jour |
| flow_traders | Flow Traders | https://www.flowtraders.com/careers/job-search/ | À jour |
| g_research | G-Research | https://gresearch.wd103.myworkdayjobs.com/G-Research | À jour |
| gelber | Gelber Group | https://www.gelbergroup.com/careers/ | À jour |
| geneva_trading | Geneva Trading | https://www.genevatrading.com/careers-open-positions/ | À jour |
| gmo | GMO | https://jobs.lever.co/gmo | À jour |
| goldman_campus | Goldman Sachs | https://higher.gs.com/campus | À jour |
| goldman_sachs | Goldman Sachs | https://higher.gs.com/results | À jour |
| graham | Graham Capital Management | https://www.grahamcapital.com/careers/ | À jour |
| graviton | Graviton Research Capital | https://job-boards.greenhouse.io/gravitonresearchcapital | À jour |
| greenland | Greenland Investment Management | https://job-boards.greenhouse.io/greenlandinvestmentmanagement | À jour |
| gsa_capital | GSA Capital | https://www.gsacapital.com/join-us | À jour |
| headlands | Headlands Technologies | https://www.headlandstech.com/careers/ | À jour |
| hsbc_graduates | HSBC | https://www.hsbc.com/careers/students-and-graduates/find-a-programme | Collecte ancienne |
| hsbc_professionals | HSBC | https://portal.careers.hsbc.com/careers | Collecte ancienne |
| hudson_river_trading | Hudson River Trading | https://www.hudsonrivertrading.com/careers/ | À jour |
| imc | IMC | https://www.imc.com/us/search-careers | À jour |
| ing | ING | https://ing.wd3.myworkdayjobs.com/ICSGBLCOR | À jour |
| invesco | Invesco | https://invesco.wd1.myworkdayjobs.com/IVZ | À jour |
| jane_street | Jane Street | https://www.janestreet.com/join-jane-street/open-roles/ | À jour |
| jefferies_campus | Jefferies | https://jefferies.tal.net/vx/lang-en-GB/mobile-0/appcentre-ext/brand-4/candidate/jobboard/vacancy/2/adv/ | Échec récent |
| jump_trading | Jump Trading | https://www.jumptrading.com/careers | À jour |
| laurion | Laurion Capital Management | https://job-boards.greenhouse.io/laurioncapitalmanagement | À jour |
| lazard_campus | Lazard | https://icbpjb.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2 | À jour |
| lseg | LSEG | https://lseg.wd3.myworkdayjobs.com/Careers | À jour |
| macquarie | Macquarie | https://recruitment.macquarie.com/en_US/careers/SearchJobs/ | À jour |
| mako | Mako | https://www.mako.com/opportunities | À jour |
| man_group | Man Group | https://www.man.com/careers | À jour |
| marex | Marex | https://www.marex.com/careers/career-opportunities | À jour |
| marshall_wace_graduates | Marshall Wace | https://www.mwam.com/join-us/early-careers/ | À jour |
| maven_securities | Maven Securities | https://www.mavensecurities.com/jobs/ | À jour |
| millennium_campus | Millennium | https://campusjobs.mlp.com/careers?domain=mlp.com&microsite=campus-site | À jour |
| millennium_professionals | Millennium | https://career.mlp.com/careers?domain=mlp.com | À jour |
| mizuho | Mizuho | https://mizuho.wd1.myworkdayjobs.com/mizuhoamericas | À jour |
| morgan_stanley | Morgan Stanley | https://ms.wd5.myworkdayjobs.com/External | À jour |
| morgan_stanley_campus | Morgan Stanley | https://morganstanley.tal.net/vx/lang-en-GB/candidate/jobboard/vacancy/1/adv | À jour |
| nomura_campus | Nomura | https://nomuracampus.tal.net/vx/lang-en-GB/mobile-0/appcentre-ext/brand-4/xf-3348347fc789/candidate/jobboard/vacancy/1/adv/ | Collecte ancienne |
| nomura_professionals | Nomura | https://careers.nomura.com/Nomura?locale=en_US | Collecte ancienne |
| nordea | Nordea | https://careers.nordea.com/ | À jour |
| northern_trust | Northern Trust | https://ntrs.wd1.myworkdayjobs.com/northerntrust | À jour |
| old_mission | Old Mission | https://www.oldmissioncapital.com/careers/ | À jour |
| optiver | Optiver | https://www.optiver.com/join-us/jobs | À jour |
| pdt | PDT Partners | https://pdtpartners.com/careers | À jour |
| pimco | PIMCO | https://pimco.wd1.myworkdayjobs.com/pimco-careers | À jour |
| point72 | Point72 | https://careers.point72.com/ | À jour |
| quadrature | Quadrature Capital | https://www.quadrature.ai/careers/join-us/ | À jour |
| quantbot | Quantbot Technologies | https://www.quantbot.com/careers/ | À jour |
| qube_research | Qube Research & Technologies | https://job-boards.greenhouse.io/quberesearchandtechnologies | À jour |
| radix_campus | Radix Trading | https://job-boards.greenhouse.io/radixuniversity | À jour |
| radix_professionals | Radix Trading | https://job-boards.greenhouse.io/radixexperienced | À jour |
| rbc | RBC | https://rbc.wd3.myworkdayjobs.com/RBCGLOBAL1 | Échec récent |
| rothschild_campus | Rothschild & Co | https://www.rothschildandco.com/en/careers/students-and-graduates/opportunities/ | À jour |
| santander | Santander | https://santander.wd3.myworkdayjobs.com/SantanderCareers | À jour |
| schonfeld | Schonfeld | https://www.schonfeld.com/careers/ | À jour |
| scotiabank | Scotiabank | https://jobs.scotiabank.com/ | Échec récent |
| sculptor | Sculptor Capital | https://sculptor.wd12.myworkdayjobs.com/Sculptor_External_Career_Site | À jour |
| shell | Shell | https://shell.wd3.myworkdayjobs.com/ShellCareers | À jour |
| smbc | SMBC | https://careersemea.smbcgroup.com/ | À jour |
| societe_generale | Société Générale | https://careers.societegenerale.com/fr/Technical/toutes-les-offres | À jour |
| squarepoint_capital | Squarepoint Capital | https://www.squarepoint-capital.com/open-opportunities | À jour |
| state_street | State Street | https://statestreet.wd1.myworkdayjobs.com/Global | Échec récent |
| sig | Susquehanna | https://careers.sig.com/jobs | À jour |
| t_rowe_price | T. Rowe Price | https://troweprice.wd5.myworkdayjobs.com/TRowePrice | À jour |
| td | TD | https://td.wd3.myworkdayjobs.com/TD_Bank_Careers | À jour |
| tower_research | Tower Research Capital | https://tower-research.com/roles/ | À jour |
| tp_icap | TP ICAP | https://tp.wd107.myworkdayjobs.com/TP-ICAP | À jour |
| trafigura | Trafigura | https://trafigura.wd3.myworkdayjobs.com/TrafiguraCareerSite | À jour |
| transmarket_group | TransMarket Group | https://www.transmarketgroup.com/careers | À jour |
| trexquant | Trexquant Investment | https://apply.workable.com/trexquant/ | À jour |
| tudor | Tudor Group | https://job-boards.greenhouse.io/tudorgroup | À jour |
| us_bank | U.S. Bank | https://usbank.wd1.myworkdayjobs.com/US_Bank_Careers | Échec récent |
| ubs | UBS | https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5131&PageType=searchResults&SearchType=linkquery&LinkID=15232 | À jour |
| ubs_professionals | UBS | https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=searchResults&SearchType=linkquery&LinkID=15231 | À jour |
| verition | Verition | https://www.verition.com/open-positions | À jour |
| viking | Viking Global Investors | https://job-boards.greenhouse.io/vikingglobalinvestors | À jour |
| virtu_financial | Virtu Financial | https://www.virtu.com/careers/ | À jour |
| walleye_capital | Walleye Capital | https://walleyecapital.com/careers | À jour |
| wellington | Wellington Management | https://wellington.wd5.myworkdayjobs.com/External | À jour |
| wells_fargo | Wells Fargo | https://wf.wd1.myworkdayjobs.com/WellsFargoJobs | À jour |
| winton | Winton | https://job-boards.eu.greenhouse.io/winton | À jour |
| worldquant | WorldQuant | https://job-boards.greenhouse.io/worldquant | À jour |
| xantium | Xantium | https://job-boards.greenhouse.io/xantium | À jour |
| xtx_markets | XTX Markets | https://www.xtxmarkets.com/careers/ | À jour |
