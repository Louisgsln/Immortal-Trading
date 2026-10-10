# Audit des employeurs et du flux — 10 octobre 2026

## Ce qui a été mesuré

Le VPS surveillait 25 sources, contre 86 activées dans la configuration de
construction. Le profil de production comporte désormais **63 sources pour
56 employeurs**, après ajout de 38 portails pour 36 employeurs distincts.
Les 30 définitions historiques et les réglages du propriétaire sont conservés.
43 catalogues Greenhouse ont été relus deux fois : cinq existants et 38 ajouts.
Old Mission et Point72 ont été relus après correction de leurs contrats publiés.
Les portails bancaires existants sont observés par leur état et leurs collectes ;
la réussite d'un catalogue ne prouve pas une couverture exhaustive de ses métiers.

| Mesure | Avant extension | Après extension |
|---|---:|---:|
| Sources activées sur le VPS | 25 | 63 |
| Offres connues en base | 1 013 | 1 320 |
| Offres du premier import des ajouts | — | 307 |
| Premier import avec score ≥70 | — | 78 |
| Premier import actuellement à examiner | — | 69 |
| Alertes créées par cet import | — | 0 |

Le flux des sept jours **avant extension** était de 80 premières découvertes,
30 au seuil et 19 alertes envoyées. Il comprend déjà 19 fiches du premier import
Morgan Stanley campus, dont 11 au seuil : hors ce premier import, 61 découvertes
et 19 au seuil. Les alertes envoyées suivent leurs règles propres.

Après ajout, le bilan de consultation affiche 387 découvertes sur sept jours,
108 au seuil et 89 à examiner. Il comprend les 307 fiches importées aujourd'hui :
ce volume ne représente ni des publications récentes ni une prévision hebdomadaire.
Le seuil reste 70 et les points restent fondés sur les faits des annonces.
Les neuf fiches du nouvel import au seuil mais indisponibles à l'examen sont des
stages dont le format ciblé reste non confirmé ; quatre ont aussi une année
inconnue. À l'inverse, le Quant Trader Internship 2027 (6 months) de Maven est
reconnu comme stage long 2027, avec un score observé de 98.

## Portails ajoutés : catalogues et stock effectivement importé

Deux lectures publiques réussies par source, puis première collecte réussie
sur le VPS pour les 38 sources. Les postes de catalogue incluent les métiers
hors cible ; la colonne score est distincte de l'éligibilité complète aux alertes.
Acadian a un catalogue valide sans fiche ciblée retenue.

| Employeur / portail | Postes du catalogue | Fiches importées | Score ≥70 |
|---|---:|---:|---:|
| 3Red Partners | 9 | 3 | 1 |
| AQR | 53 | 3 | 1 |
| Acadian Asset Management | 15 | 0 | 0 |
| Akuna Capital | 41 | 10 | 2 |
| Aquatic Capital Management | 7 | 4 | 0 |
| Chicago Trading Company / chicago_trading | 24 | 3 | 1 |
| Chicago Trading Company / chicago_trading_campus | 8 | 5 | 1 |
| DV Trading | 69 | 21 | 13 |
| Da Vinci | 16 | 10 | 2 |
| Engineers Gate | 10 | 4 | 0 |
| Five Rings | 17 | 5 | 3 |
| Gelber Group | 11 | 10 | 5 |
| Geneva Trading | 14 | 5 | 2 |
| Graham Capital Management | 11 | 1 | 0 |
| Graviton Research Capital | 21 | 7 | 1 |
| Headlands Technologies | 8 | 2 | 0 |
| Hudson River Trading | 89 | 10 | 1 |
| Mako | 5 | 3 | 1 |
| Man Group | 56 | 8 | 0 |
| Marshall Wace | 6 | 1 | 0 |
| Maven Securities | 44 | 10 | 6 |
| Old Mission | 38 | 20 | 12 |
| PDT Partners | 11 | 2 | 0 |
| Point72 | 221 | 31 | 3 |
| Quantbot Technologies | 7 | 5 | 0 |
| Qube Research & Technologies | 193 | 23 | 5 |
| Radix Trading / radix_campus | 8 | 2 | 0 |
| Radix Trading / radix_professionals | 7 | 1 | 0 |
| Schonfeld | 69 | 11 | 0 |
| Squarepoint Capital | 93 | 15 | 4 |
| Tower Research Capital | 94 | 22 | 2 |
| TransMarket Group | 18 | 4 | 4 |
| Tudor Group | 4 | 2 | 0 |
| Verition | 27 | 4 | 0 |
| Virtu Financial | 47 | 21 | 5 |
| Walleye Capital | 12 | 3 | 1 |
| Winton | 8 | 1 | 0 |
| WorldQuant | 95 | 15 | 2 |

## Vérification des catalogues existants

Deux lectures stables ; les scores sont ceux des annonces sélectionnées pendant
l'audit, ils ne représentent pas les nouvelles offres hebdomadaires.

| Employeur | Postes examinés | Fiches sélectionnées | Score ≥70 |
|---|---:|---:|---:|
| Jump Trading | 107 | 25 | 11 |
| XTX Markets | 7 | 1 | 0 |
| Flow Traders | 47 | 11 | 8 |
| IMC | 175 | 28 | 16 |
| DRW | 176 | 29 | 10 |

## Corrections et prochains candidats à qualifier

Les contrats Old Mission `Intern` et Point72 `Part Time` sont désormais reconnus.
Les deux programmes de recherche Old Mission 2027 retenus décrivent des missions
liées aux décisions de trading et à la modélisation des options ; leurs scores
observés sont respectivement 86 et 92. La réconciliation de 33 champs dérivés,
dont 11 scores historiques, retire aussi les anciens faux positifs Associate.
L'audit final des 1 320 fiches ne trouve aucun écart avec le moteur actif.

Le rejet de titre ou le score nul peut aussi cacher une annonce à examiner.
Les exemples suivants sont au carnet, sans score inventé ni alerte forcée :

| Source / référence publique | Observation | Prochaine vérification |
|---|---|---|
| Jump Trading 8027898 | Campus Quantitative Researcher (Off-Cycle - Winter/Spring 2027 Intern), rejet `no_title_match` | Lire les missions, dates et exigences ; vérifier le lien au trading |
| Flow Traders 8156203, 8213037, 8266897 | PhD Graduate Quantitative Researcher, rejet `no_title_match` | Vérifier les missions et le diplôme réellement exigé avant élargissement |
| Point72 7318005002 et variantes Cubist | Annonces collectées, score nul faute de qualification de recherche retenue | Identifier les rubriques de missions et contre-exemples ; distinguer profils juniors et expérimentés |

Chaque prochaine règle doit utiliser une annonce complète, les conditions du
candidat et des contre-exemples testables pour démontrer la pertinence du rôle.

## Stages et santé réelle

Off-cycle et stages longs **2027** sont activés, Summer hors alertes. L'extension
retire à la collecte les exclusions générales de stages dans 23 configurations,
sans changer les exclusions de métiers ou d'employeurs. Les filtres d'alerte
vérifient ensuite format, année, échéance, score, fraîcheur et suivi.
31 fiches satisfont les critères de stage au contrôle final ; 61/63 références
stages sont validées. Cela n'annonce pas 31 nouveaux messages Telegram.

Au contrôle du 10 octobre à 07:51 UTC : 58/63 sources fraîches. BNP reste ancien
après HTTP 403 ; Optiver est partiel pour une fiche non vérifiable. Barclays,
Morgan Stanley et Citi ont un échec récent ; Deutsche Bank a repris. Aucun refus
d'accès ne ferme automatiquement des offres. Nomura campus reste en attente si
CAPTCHA, conformément au choix du propriétaire. Un contrôle complémentaire a
relevé 57 sources fraîches après une pagination incohérente chez Nomura
professionnels ; l'import est interrompu et la reprise suit la cadence prévue.
Cet incident professionnel est distinct du CAPTCHA campus.

Le watcher est actif, le récapitulatif Telegram est configuré à 09:00 Paris,
les cinq conteneurs tournent. Le statut de santé du radar peut rester dégradé
ou critique à cause d'une source ancienne malgré l'activité du watcher.
Le Dashboard répond via le même lien HTTPS privé, avec suivi modifiable.

Le [carnet actif](TASK-BOARD.md) relie les résultats installés aux prochains
travaux. Les anciennes lignes Windows sont classées comme historique.
Preuves : [DELIVERY-LOTS125-127.json](DELIVERY-LOTS125-127.json),
[DELIVERY-LOT128.json](DELIVERY-LOT128.json) et
[VALIDATION-LOT128.md](VALIDATION-LOT128.md).
