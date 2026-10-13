# Validation — lot 162 : informations des opportunités

Installé sur `vps-b7a073e2.vps.ovh.net` le 13 octobre 2026. Application `17eb80a0bcb75a0380efe2b86f36406ae2936947`, image `immortal-trading:lot162-opportunity-fields-20261013`.

## Informations affichées

Les quatre champs partagent désormais la même extraction dans Telegram et le Dashboard : localisation, début, expérience et échéance. Le Dashboard propose les extraits employeur et la date réelle de vérification de la fiche. Les champs des anciennes offres sont calculés à la lecture ; aucune identité, localisation stockée, ancienneté ou date manquante n'est réécrite dans la base.

L'extraction conserve les qualificatifs des critères d'expérience : souhaité, préféré ou obligatoire. Une expérience sans durée chiffrée reste distincte d'un minimum en années. Les dates de début précises sont retenues lorsqu'elles sont explicites ; les périodes, alternatives, conflits, dates numériques ambiguës et dates sans année restent distingués. Les dates françaises et les indications ASAP, à convenir et recrutement au fil de l'eau sont reconnues. Une formule comme « start your career » ne devient pas une date. Les localisations multi-adresses HSBC restent triées et lisibles.

## Témoin UBS

Le portail officiel UBS a été relu : offre 351976, référence 344425BR, intitulé actuel **eFX Crypto Trader**, Singapour. La description complète exige une expérience préalable dans une entreprise d'actifs numériques ou un desk eFX ; elle ne donne pas de minimum d'années. Les champs structurés du portail ne publient ni date de début ni date de clôture. `lastupdated` n'est pas une date de début ou d'échéance.

| Champ | Résultat vérifié |
|---|---|
| Localisation | Singapour (SG) |
| Début | Date non indiquée par l'employeur |
| Expérience | Expérience préalable en actifs numériques ou desk eFX · durée non chiffrée |
| Échéance | Date non indiquée par l'employeur |

Les informations absentes ne sont pas complétées avec une année de programme, une date de publication, une date de diplôme, le siège de l'entreprise ou le score. Une information présente mais ambiguë conserve son extrait pour vérification. « Non indiqué » décrit les informations officielles effectivement collectées, pas une garantie qu'aucune page secondaire ne contient de précision.

## Contrôles

- Contrôles ciblés d'extraction, dates, HSBC, UBS et Dashboard réussis ; Ruff et Mypy (126 modules) réussis.
- [CI du correctif](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38383492429) : 5 400 tests Python 3.14 réussis, 34 tests JavaScript réussis ; autres versions et récupération de conteneur en cours au premier relevé.
- Image Docker construite ; contrat des assets validé, 89 contrôles et 7 modules, empreintes CSS/JavaScript vérifiées.
- Chromium sur une base synthétique, écran 390 × 844 : quatre champs UBS, ouverture de l'extrait officiel, dates absentes explicites ; ajout aux souhaits, réception d'une modification simulée depuis Telegram, tri, Postulé conservant le favori, retrait conservant la candidature ; zéro erreur JavaScript.
- Simulation sans réseau sur copie de 1 591 fiches, dont 1 575 actives : deux lectures, toutes les tables inchangées, souhaits inchangés, sauvegarde et restauration vers des chemins neufs vérifiées ; zéro appel Telegram.
- Production : sauvegarde version 2 vérifiée avant déploiement ; schéma 4 et inode de la base, anciens identifiants, candidatures, alertes envoyées, historiques, souhaits et leur historique préservés. Liaison Telegram, curseur monotone, digest et liaison des messages d'état conservés. Aucune restauration de la base active.
- Cinq services Docker en fonctionnement ; quatre services système actifs et activés au démarrage ; Dashboard accessible par le même lien HTTPS privé sans connexion. Les alertes de chaque nouvelle offre, même à 0, restent activées ; off-cycle et stages longs 2027 restent inclus.

Une seule fiche UBS corrigée a été envoyée dans Telegram avec accusé de réception confirmé et bouton des souhaits. Cet aperçu ne réécrit pas le journal des alertes ni le curseur. Le contrôle HTTPS réel valide les garde-fous 404/405/403 et les API des souhaits/candidatures. Le relevé indique 85 sources à jour sur 91 ; Nomura campus, BNP général/campus, Jefferies campus, Morgan Stanley campus et Wellington restent à surveiller à cette date. Le chargement de 1 591 fiches a pris 22,434 secondes ; le lot 159 de performance reste ouvert.

## Mesure datée à la mise en ligne

Sur **1 575 fiches actives** :

| Champ | Informations reconnues | À vérifier ou absentes |
|---|---|---|
| Localisation | 1 502 pays/localisations reconnus | 72 localisations non reconnues, 1 non publiée |
| Début | 68 dates exactes, 81 périodes mensuelles, 18 années et 28 indications qualitatives | 62 valeurs à interpréter, 19 conflits, 1 299 sans date publiée dans les données collectées |
| Expérience | 461 minimums chiffrés et 105 critères non chiffrés | 1 009 sans minimum reconnu dans les données collectées |
| Échéance | 35 dates, 16 instants et 20 recrutements au fil de l'eau | 34 indications à interpréter, 1 470 sans date publiée dans les données collectées |

Les compteurs ne prouvent pas que chaque employeur publie ces quatre champs. Les écarts avec la simulation reflètent aussi les collectes ordinaires poursuivies pendant le déploiement. Le profil reste à **91 sources / 79 employeurs** ; la fraîcheur courante est donnée par `/statuts`, pas par un ancien relevé.

[Preuves JSON](DELIVERY-LOT162.json) · [Carnet des tâches](TASK-BOARD.md).
