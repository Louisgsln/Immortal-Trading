# Lots 148–150 — HSBC et état quotidien du radar, 12 octobre 2026

Correctifs installés sur OVH : `immortal-trading:lot148-hsbc-radar-status-20261012`.
Code publié : `cd0af853f6d54feb5762b25f6142ae445693067e`.
[Preuves de livraison](DELIVERY-LOTS148-150.json), [79 sources](RADAR-SOURCES-20261012.md),
[carnet](TASK-BOARD.md).

## 148 — Mises à jour HSBC

L'offre employeur `1370782657`, « Markets - Sales and Trading - Graduate »,
alterne l'ordre de Shenzhen, Beijing et Shanghai. Les cinq alertes de mise à jour
déjà envoyées correspondaient au même ensemble d'adresses ; les autres champs
de contenu étaient identiques dans les six versions historiques vérifiées.

Le collecteur trie les adresses. La comparaison en base et la qualification des
changements comparent le même ensemble d'adresses, y compris pour les anciennes
fiches. La règle est limitée aux adresses multiples du portail HSBC graduates.
Une ville ajoutée ou retirée, une région ou un pays modifié restent un changement réel.
La carte Telegram affiche « Beijing · Shanghai · Shenzhen · Chine ».

Sur copie de la base : six versions historiques et six permutations rejouées,
zéro version et zéro alerte supplémentaires, suivi et historiques identiques.
Le retrait d'une ville crée une mise à jour sur cette copie isolée.
En production, l'offre est vérifiée à `2026-10-12T13:14:36.289346+00:00`,
avec toujours six versions, son identifiant conservé et son score de 92/100.
La date de dernière modification matérielle reste celle du 12 octobre à 02:10 UTC.
Les anciennes alertes restent dans l'historique.

## 149 — État quotidien dans Telegram

Le récapitulatif activé à **09:00, Europe/Paris** inclut maintenant l'activité du
radar, son dernier signal, les sources et employeurs surveillés, les sources à jour
et le seuil des alertes. Ce bloc apparaît même sans nouvelle offre admissible.
Le contrôle de l'horaire précède la réception des commandes Telegram : un échec
de `getUpdates` ne reporte plus systématiquement le récapitulatif.

Une tentative par date est conservée avant l'envoi. Les redémarrages, changements
d'heure et rattrapages restent protégés contre les doublons ; le curseur, la liaison
propriétaire et les préférences existantes sont conservés. Les avis d'incident,
actuellement désactivés, sont indépendants de ce message quotidien.

Le journal confirme `telegram_digest_delivered day=2026-10-12` après installation.
Un message distinct de confirmation des correctifs a aussi reçu un accusé Telegram :
un envoi, zéro message d'offre. Son marqueur privé est enregistré avant l'appel,
sans réessai automatique en cas d'incertitude. Aucun réglage quotidien n'a été réinitialisé.

## 150 — Activité continue et couverture

Le contrôle Docker vérifie la base compatible et le signal du worker actif.
Les refus d'accès d'un employeur restent des problèmes de couverture dans
`/statuts`, le Dashboard et le récapitulatif ; ils ne déclarent plus à tort le worker arrêté.
Un signal ancien, un collecteur arrêté ou une base illisible font toujours échouer le contrôle.

Au relevé `2026-10-12T13:20:12.679624+00:00` : **79 sources / 67 employeurs**, **73 à jour**.
Les sources activées sont programmées en continu selon leur cadence et leurs délais de reprise.
Les six sources à surveiller sont Nomura campus (CAPTCHA), BNP général (ancien),
Morgan Stanley professionnels (partiel), Jefferies campus, Citi campus et BNP campus (échec récent).
Ces problèmes restent ouverts au carnet. Nomura attend toujours l'intervention humaine choisie
par le propriétaire. L'activité H24 ne garantit pas un accès réussi à chaque portail.

Les stages **off-cycle et longs 2027** et leurs alertes restent activés ; Summer reste
hors alertes. `/statuts` et `/status` présentent le même total ; `/sources` expose les 79 portails.

## Installation et vérifications

Sauvegarde ZIP vérifiée avant installation et à nouveau après observation.
Schéma SQLite 4, inode, identités, candidatures, lignes de suivi, alertes envoyées et
historiques conservés. Le curseur Telegram reste monotone et sa liaison inchangée.
La base compte 1 506 fiches avant installation, puis 1 509 lors du relevé : les collectes continuent.
Aucune restauration de base ni réinitialisation de l'état Telegram.

Cinq services Docker actifs, zéro redémarrage des nouveaux conteneurs au contrôle final ;
radar et Dashboard sains. Quatre unités systemd actives et activées.
Même lien HTTPS privé éditable, certificat vérifié ; 86 contrôles et sept modules vérifiés.
Accès public et fichiers privés 404, POST page privée 405, API sans CSRF 403.
Les 33 commandes bloquées Remote Desktop Commander, dont `sudo`, sont rétablies.

CI [38214592402](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38214592402) :
six jobs réussis, **5 311 tests par version Python 3.11–3.14**, couverture 96 %, **34 tests Node**,
Ruff, mypy, contrat du Dashboard empaqueté et récupération du conteneur isolé réussis.
Les preuves et l'inventaire publiés ne contiennent ni lien privé ni état Telegram personnel.
