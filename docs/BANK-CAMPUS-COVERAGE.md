# Banques et campus — carnet de couverture du 10 octobre 2026

Périmètre : métiers de trading, marchés et recherche habituels, plus stages
off-cycle et longs de 2027. Le seuil reste 70/100. Summer et Associate seul
restent exclus ; Analyst/Associate conserve son traitement existant.

## Portails vérifiés pour les lots 129–131

Les sept sources ajoutées ci-dessous sont installées et ont réussi leur premier
import sur OVH : 54 fiches, 13 au seuil de 70, zéro alerte d'import. Le profil
actif compte 70 sources pour 62 employeurs. Les trois campus bloqués restent ouverts.

| Banque / source | Catalogue et périmètre | Contrôle public / limite |
|---|---|---|
| Bank of America campus | Recherche étudiants officielle, distincte des événements et professionnels | 107 annonces paginées ; témoin Milan 15033 confirmé, 96/100 ; autres Sales & Trading à Paris, Francfort et Stockholm |
| Bank of America professionnels | Workday `ghr/lateral-us` | 459 résultats distincts dans les recherches ciblées, 11 fiches retenues ; ne couvre pas le campus |
| Jefferies campus | Oleeo Campus Opportunities, tableau 2 | Tableau 1 = Events ; 61 annonces ; premier succès : trois fiches ; témoin Fixed Income off-cycle Dubaï 2002 à 82/100 |
| RBC | Workday `rbc/RBCGLOBAL1` | Trading, trader, quantitative, structuring, markets, off-cycle, internship ; 571 résultats distincts, 11 fiches retenues ; une Summer ne devient pas une alerte |
| ING | Workday `ing/ICSGBLCOR` | 190 résultats distincts, six fiches ; quatre stages collectés, année/format non déduits d'une simple mention d'internship |
| Wells Fargo | Workday `wf/WellsFargoJobs`, familles publiques ciblées | 19 résultats distincts, deux fiches ; aucun off-cycle 2027 ciblé établi par cette lecture |
| Santander | Workday officiel relié depuis Santander CIB | 232 résultats distincts, 11 fiches ; recherche partielle ; filtre campus officiel relu, sans résultat ciblé avec `scib` |
| JPMorgan campus | Oracle `CX_1001` | HTTP 403 observé depuis OVH ; source désactivée conservée, pas déclarée surveillée |
| NatWest campus | Pages early careers officielles | HTTP 403 ; intégration laissée ouverte |
| Nomura campus | Portail public distinct des professionnels | Validation humaine du CAPTCHA laissée en attente sur décision du propriétaire |

Les recherches Workday ne sont pas un inventaire exhaustif de chaque banque.
Les plafonds sont 500 résultats par requête et 80 détails ; un dépassement ou une
pagination incohérente est un échec explicite, jamais un import tronqué déclaré
réussi. Pour RBC, `markets` retournait 482 annonces au contrôle ; ce volume est
à surveiller. Les programmes non ouverts aujourd'hui ne sont pas inventés.

## Exploitation et architecture

Les sept ajouts utilisent l'ordonnanceur permanent du VPS, avec une cadence de
30 minutes par source, indépendante du poste de développement. Une collecte
longue ne bloque pas les autres portails. Le client HTTP conserve les délais
par hôte et les règles `robots.txt` ; aucun CAPTCHA ou refus d'accès n'est contourné.

Le portail campus Bank of America énumère le catalogue étudiants ; son Workday
professionnel reste distinct. Chez Jefferies, le tableau des opportunités est
séparé des événements. L'identifiant de l'annonce, les métadonnées, le contenu
et la destination publique de candidature doivent concorder avant stockage.
Les collecteurs campus refusent explicitement une pagination incohérente et ne
déduisent pas la clôture des anciennes offres à partir d'une absence.

Le premier import est silencieux. Ensuite, les alertes appliquent le seuil,
la fraîcheur de la source, le suivi de candidature, les dates et les critères
de programme habituels. Un stage sans format ou année confirmés reste visible
mais ne devient pas automatiquement une alerte off-cycle 2027.

## Offres témoins et critères de clôture

[BANK-CAMPUS-REFERENCE.json](BANK-CAMPUS-REFERENCE.json) conserve sept identités
publiques vérifiées indépendamment de la base locale. Avec le profil, la base
de l'instance à contrôler et le fichier de référence accessibles, la commande
en lecture seule suivante mesure leur présence et leur score stocké :

```bash
trading-radar coverage --reference docs/BANK-CAMPUS-REFERENCE.json
```

L'image Docker ne contient pas le dossier `docs`. Le contrôle de livraison
transmet donc la référence à un fichier temporaire du conteneur ou la monte
explicitement en lecture seule ; il ne modifie pas la base de production.

Ce pourcentage porte uniquement sur ces témoins, pas sur l'ensemble du marché.
La présence d'une fiche, un score au seuil et l'éligibilité effective à une
alerte sont trois contrôles distincts. Une source ancienne, une candidature
déjà envoyée, un programme hors cible ou une échéance dépassée peuvent retenir
une annonce pourtant bien collectée.

Pour clôturer un portail : catalogue/détails vérifiés, tests positifs et négatifs,
image construite, copie de la base importée sans envoi, sauvegarde vérifiée,
installation OVH, premier succès et témoin retrouvé. Les preuves de livraison
sont consignées dans [VALIDATION-LOTS129-131.md](VALIDATION-LOTS129-131.md).

## Tâches suivantes

1. Portails étudiants Barclays, Citi et Deutsche Bank : vérifier les accès et
   offres témoins avant de les compter dans la couverture campus.
2. Bank of America Global Quantitative Research 14722 et Jefferies Quant Fulltime
   1954 : fiches collectées, qualification des missions à auditer ; le nom de la
   banque et un titre quantitatif ne suffisent pas à créer un bon score.
3. RBC : surveiller le plafond de la requête `markets` et isoler des partitions
   publiques plus précises si le catalogue grandit.
4. ING et Santander : contrôler les campagnes européennes et les dates de début
   publiées ; conserver « non confirmé » pour les formats/années inconnus.
5. JPMorgan, NatWest, BNP et Nomura : reprendre les accès accessibles publiquement,
   conserver l'historique et laisser les blocages visibles dans le carnet principal.
