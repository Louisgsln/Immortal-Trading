# Lots 151–153 — messages réguliers et sources, 12 octobre 2026

Installés sur OVH : `immortal-trading:lot151-status-sources-20261012`.
Code publié : `09212e9482231915e189eacb6c90f6779f7e9286`.
[Preuves](DELIVERY-LOTS151-153.json), [85 sources](RADAR-SOURCES-LOTS151-153.md), [carnet](TASK-BOARD.md).

## 151 — Trois points d'état par jour

Le récapitulatif existant reste activé à **09:00, Europe/Paris**. Deux messages
supplémentaires d'état sont activés à **13:00 et 18:00**, même sans offre nouvelle.
Ils affichent l'activité du collecteur, son dernier signal, les sources et employeurs
surveillés, la fraîcheur et le seuil. Un radar arrêté ou sans signal n'est pas annoncé actif.

Les tentatives sont conservées dans un fichier indépendant du curseur et des préférences
du digest. La liaison propriétaire est contrôlée. Une tentative par créneau est enregistrée
avant l'appel Telegram ; une livraison incertaine ne déclenche pas de réessai automatique.
Un redémarrage ne duplique pas un créneau. Le rattrapage des points supplémentaires
est limité à une heure, au dernier créneau seulement. Les changements d'heure sont gérés
en Europe/Paris. Un créneau déjà couvert par le récapitulatif ne produit pas deux messages.

L'activation du 12 octobre est postérieure à 13:00 : aucun état rétroactif n'a été envoyé.
Le prochain point supplémentaire est **18:00 le 12 octobre**, puis les trois horaires habituels.
Un message distinct de confirmation a reçu un accusé Telegram après installation :
un envoi, zéro message d'offre. Le récapitulatif de 09:00 avait été confirmé lors des
lots 148–150 ; son journal appartient au conteneur précédent, remplacé pendant cette livraison.

## 152 — Cohérence et activité réelle

Les recherches Workday paginées des six ajouts, de Citi campus et de Morgan Stanley
recontrôlent la première page après pagination, avec les mêmes facettes et la même requête.
Un changement de total, titre, chemin, localisation ou référence reporte la collecte.
L'ordre des résultats et l'âge d'affichage « Today/Yesterday » n'introduisent pas de faux échec.
Les plafonds et budgets restent explicites ; aucun catalogue tronqué n'est déclaré complet.

Citi campus utilise les mêmes contrôles de référence opaque que son catalogue professionnel :
identité exacte et titre public concordant avant de retirer une lacune hors périmètre.
Une référence ambiguë ou inaccessible reste signalée. Les recherches ciblées ne ferment
aucune ancienne offre par absence. Citi campus et Morgan Stanley ont réussi la lecture
avec recontrôle avant bascule ; leur reprise reste suivie au lot 147.

Le rapport capture le signal du radar avant les contrôles plus lents de la base :
un nouveau signal écrit pendant le contrôle ne devient plus artificiellement « futur ».
La programmation reste indépendante des échecs de réception des commandes Telegram.

## 153 — Six employeurs supplémentaires

| Source | Fiches importées | Score ≥70 | Stages admissibles 2027 ≥70 |
|---|---:|---:|---:|
| PIMCO | 18 | 1 | 0 |
| BlackRock | 13 | 0 | 0 |
| CIBC | 0 | 0 | 0 |
| TD | 2 | 0 | 0 |
| G-Research | 5 | 0 | 0 |
| TP ICAP | 11 | 2 | 0 |

Catalogues publics Workday et détails contrôlés deux fois, puis revalidés avant installation.
Cadence de 30 minutes ; requêtes espacées de deux secondes, budgets de 600 secondes,
500 résultats par requête et 80 détails par source. Le profil actif conserve les stages
off-cycle et longs 2027. Les Summer restent hors alertes. Les dates et formats inconnus
ne deviennent pas artificiellement admissibles.

**49 nouvelles fiches**, base **1 509 → 1 558**, import sans alerte. Deux scans sur copie :
49 nouveautés au premier, zéro changement au second, zéro appel au notifier.
Les trois scores au seuil appartiennent à des offres professionnelles ; aucun stage
supplémentaire de ces sources n'est entièrement admissible au seuil lors de ce relevé.
Ce premier import ne représente ni des publications récentes ni un débit hebdomadaire garanti.

CIBC a 107 références distinctes examinées et zéro titre retenu dans les filtres actuels.
Le témoin « Analyst/Associate, Fixed Income, Currency and Commodity », référence 2619877,
décrit une couverture clients avec pricing, execution et booking de transactions, et 0–3 ans
d'expérience. Il est écarté par le filtre de titre et classé NON_TRADING par les règles actuelles.
Sa qualification métier devient une tâche explicite au lot 133 ; aucun score n'a été gonflé.

## Conservation, installation et limites

Les collectes réelles ont été préparées avant l'arrêt du radar. Les instantanés ont été
vérifiés par SHA-256 et importés pendant la bascule, sans accès réseau ni alertes.
Sauvegarde ZIP vérifiée avant installation et après observation. Schéma SQLite 4, inode,
identités, lignes de suivi, candidatures, alertes envoyées et historiques préservés.
Curseur Telegram monotone, liaison propriétaire et réglage de 09:00 conservés.
Les six nouvelles sources ont un premier succès et une référence silencieuse de stages.

Au relevé `2026-10-12T14:16:32.055254+00:00` : **85 sources / 73 employeurs**, **80 à jour**.
HSBC professionnels est en échec récent ; Nomura campus, BNP général, Jefferies campus
et BNP campus restent à surveiller. Ces états évoluent avec les reprises et restent visibles
dans `/statuts`. Nomura attend toujours l'intervention humaine choisie par le propriétaire.

Cinq services Docker actifs, radar et Dashboard sains, zéro redémarrage au contrôle final.
Quatre unités systemd actives et activées. Même lien HTTPS privé éditable ; certificat,
86 contrôles et sept modules vérifiés. Accès public et fichiers privés 404,
POST page privée 405 et API sans CSRF 403. Réponse HTTPS mesurée : 19,665 secondes.
Les 33 commandes bloquées Remote Desktop Commander, dont `sudo`, sont rétablies et vérifiées.

CI [38258320123](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38258320123) :
six jobs réussis, **5 347 tests par version Python 3.11–3.14**, couverture 96 %, **34 tests Node**,
Ruff, mypy, contrat empaqueté et récupération du conteneur isolé réussis.
Python 3.14 signale un ResourceWarning de connexion SQLite non fermée dans la suite ;
allocation à diagnostiquer au carnet, sans échec de test.
