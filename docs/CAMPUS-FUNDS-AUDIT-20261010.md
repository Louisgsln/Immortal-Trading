# Portails campus et hedge funds — audit du 10 octobre 2026

Périmètre : banques américaines, britanniques et françaises, et fonds disposant
d'offres publiques de trading, marchés, structuration ou recherche quantitative.
Les stages off-cycle et longs 2027 sont inclus ; Summer, millésimes différents et
fonctions hors cible restent exclus des alertes. Le seuil reste 70/100.
L'origine de la banque ne restreint pas les villes aux États-Unis, au Royaume-Uni
ou à la France : Milan, Francfort et les autres zones existantes restent suivis.

Les contrôles utilisent les accès publics depuis OVH, avec la politique robots
et le rythme de requêtes du radar. Aucun formulaire de candidature n'est soumis.
Une page présentant un programme n'est pas une offre ouverte. Un catalogue
partiel, un CAPTCHA, une réponse 403 ou une fiche contradictoire ne deviennent
jamais une collecte complète ni une preuve d'absence d'offres.

## Banques : accès et périmètres

| Employeur | Portail / constat public | Livraison ou tâche |
|---|---|---|
| Bank of America | Catalogue étudiants distinct des professionnels ; 2027 off-cycle Milan, Paris, Francfort, Stockholm | Sources installées aux lots 129–131 ; référence indépendante conservée |
| Goldman Sachs | `higher.gs.com/campus`, distinct du catalogue professionnels | Déjà surveillé |
| Morgan Stanley | Tal.net Global Programs, distinct du Workday professionnels | Déjà surveillé |
| Jefferies | Tal.net Campus Opportunities, distinct des événements | Déjà surveillé ; témoin Dubai 2027 |
| Citi | Page Student and Grad Programs publique, même Workday que les professionnels ; Markets Paris 2027 off-cycle retrouvé | Nouvelle source `citi_campus`, requêtes off-cycle/internship/placement ; identité employeur commune |
| Barclays | Early Careers et Internships renvoient au Workday déjà suivi | Six recherches au lieu de trading seul ; même source, aucun faux employeur supplémentaire |
| Deutsche Bank | Le JavaScript officiel publie Beesite `graduatesearch` et `jobhtml`, candidatures Recsolu/Yello | Nouvelle source `deutsche_bank_campus` ; les 81 programmes publics du catalogue ont été relus avant filtrage |
| HSBC | Catalogue programmes et portail professionnels distincts | Déjà surveillés ; campagnes et fiches ouvertes à distinguer |
| UBS | Sites étudiants 5131 et professionnels 5012 distincts | Déjà surveillés |
| Crédit Agricole CIB | Catalogue Talentsoft commun aux stages et professionnels | Déjà surveillé ; pas d'exclusion globale des stages |
| Société Générale | Catalogue public commun aux stages et professionnels | Déjà surveillé ; stages inclus dans la politique active |
| BNP Paribas | Racine française suivie encore affectée par HTTP 403 ; pages publiques anglaises lisibles durant cet audit | Adapter et vérifier les fiches anglaises et les doublons avant bascule ; conserver la source ancienne explicite |
| Lazard | La page officielle Students lie Oracle LazardStudentCareers ; numéro réel du site `CX_2` publié par cette page | Nouvelle source `lazard_campus` ; offres M&A sans missions de marchés hors cible |
| Wells Fargo, RBC, ING, Santander | Catalogues publics Workday, stages dans les recherches déjà livrées | Déjà surveillés ; année ou format inconnu reste une tâche de qualification |
| JPMorgan | Portail campus déjà refusé en 403 ; lien de programme consulté lors de cet audit redirige hors du périmètre vérifié | En attente ; pas de contournement ou de catalogue vide inventé |
| NatWest | Refus HTTP 403 constaté lors du précédent audit | En attente d'accès public exploitable |
| Standard Chartered | Early Careers lie le catalogue public SuccessFactors ; site accessible | Connecteur à développer : résultats, pagination, identité et fiches complètes |
| Lloyds Banking Group | Page Industrial Placements publique ; programmes annoncés pour l'automne 2026 | Identifier et valider les véritables offres ouvertes, pas les seules pages de présentation |
| BPCE / Natixis | Application publique JavaScript accessible, routes d'application distinctes exposées | Développer l'accès aux offres publiques et aux fiches ; ne pas utiliser les espaces de mobilité interne |
| Rothschild & Co | Catalogue étudiants public : 60 programmes, 50 au premier écran ; stages longs/off-cycle 2027 visibles | Valider pagination et fiches avant activation ; advisory hors métiers actuels n'obtient pas de score de trading |
| Nomura campus | Source déjà activée ; succès public de huit fiches constaté le 10/10 à 17:58 UTC après un échec antérieur | L'intervention humaine reste en attente si le CAPTCHA revient ; aucune session Windows créée par cet audit |

## Hedge funds et recherche : ajouts et accès restants

| Employeur | Accès / preuve | Livraison ou tâche |
|---|---|---|
| Millennium | Page officielle Students lie `campusjobs.mlp.com`, recherche anonyme Eightfold et fiches JobPosting complètes | Nouvelle source campus ; témoin Hong Kong 2026, off-cycle de 3–6 mois, détecté et correctement hors alertes 2027 |
| Capula | Site officiel lie Workable ; `llms.txt` annonce explicitement les dix offres de `jobs.md` et leurs fiches complètes | Nouveau connecteur ; compte, identifiants et deux lectures concordantes ; poste quantitativement intéressant mais explicitement spéculatif écarté |
| Point72 / Cubist, Schonfeld, Walleye, Squarepoint, Qube, Man Group, Aquatic, AQR, Winton, WorldQuant, Verition, Marshall Wace, Tudor, PDT, Graham, Quantbot, Engineers Gate, Acadian | Sources publiques déjà intégrées | Stages soumis à la même politique ; auditer les missions et formats inconnus, sans utiliser le texte général du fonds pour gonfler les scores |
| Citadel | Page carrière officielle : HTTP 403 depuis OVH | Non activé ; attente d'un accès public exploitable |
| Citadel Securities | Page carrière officielle : HTTP 403 depuis OVH | Non activé ; distinguer ce teneur de marché du fonds Citadel |
| Two Sigma | Page carrière officielle : HTTP 403 depuis OVH | Non activé |
| Balyasny | Pages Careers/Internships publiques ; lien Salesforce repéré, fonction recrutement non établie | Identifier le véritable catalogue de postes avant tout connecteur ; une présentation de stage ou un portail de relations commerciales ne suffit pas |
| Brevan Howard | Site officiel lie `careers.brevanhoward.com`, portail Phenom public accessible | Connecteur à développer et valider ; pas encore compté comme surveillé |
| Rokos Capital | Site officiel public ; pas de flux complet établi durant cet audit | Identifier le catalogue de recrutement et des fiches ouvertes |
| Oxford Asset Management | Page publique avec contact recrutement ; aucun catalogue complet établi | Ne pas convertir un contact email en source d'offres surveillée |

## Comptage et suites du carnet

Les nombres de sources comptent des périmètres de collecte activés, pas des
employeurs uniques. Deux portails d'un même employeur ne font pas deux banques.
`/statuts`, `/statut` et `/status` désignent le même état privé du radar.
`/sources`, `/sources 2`, etc. donnent l'inventaire activé avec l'état de chaque
source, par pages de trente. Le Dashboard conserve le même profil de production.
Les sources non activées ci-dessus ne sont pas ajoutées au total de surveillance.

L'inventaire final daté et les premiers succès OVH sont publiés dans
[RADAR-SOURCES-20261010.md](RADAR-SOURCES-20261010.md). Une couverture mondiale
exhaustive n'est pas prouvée : l'audit rend visibles les portails manquants et
les tâches nécessaires pour les intégrer, au lieu de les compter comme livrés.
