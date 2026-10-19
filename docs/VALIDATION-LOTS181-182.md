# Lots 181–182 — Dashboard progressif, état du radar et diagnostic des sources

Version publiée : **dfe25f6703419ab89f5fdd305d6401f8bbda3048**. Préparée sur OVH,
**pas encore installée** : Remote Desktop Commander bloque de nouveau sudo après
la fermeture de la précédente fenêtre de maintenance. Les lots 177–180 restent
la version en service. [Preuves](DELIVERY-LOTS181-182.json).

Au **19/10/2026 à 20:26 UTC**, un contrôle en lecture seule de la version actuelle
confirme le radar actif, **128 sources / 116 employeurs, 125 à jour**, et 2 019
offres enregistrées. HTTPS répond en **15,442 secondes**. Ces valeurs décrivent
la version en service, pas les performances de la nouvelle version.

## Ce qui change

- Le Dashboard privé renvoie d'abord une page légère indiquant le chargement.
  La liste complète et ses compteurs apparaissent ensemble après une lecture
  authentifiée ; un échec affiche une erreur et un bouton pour réessayer.
- L'état réel du radar est relu toutes les quinze secondes et au retour dans
  l'onglet. Une lecture indisponible affiche « Activité du radar à vérifier ».
  Ce contrôle ne recalcule ni les offres ni la santé complète des sources.
- Sur téléphone, les filtres se replient. Le bouton indique le nombre de filtres
  actifs ; les sélections restent appliquées et les dates invalides restent
  signalées même lorsque le formulaire est replié.
- Les exports HTML et les serveurs locaux ordinaires conservent leurs données
  complètes et leur fonctionnement sans connexion. Aucune migration de base.

Le même lien privé, les révisions du suivi, les souhaits, les alertes tous scores
et les stages off-cycle/longs restent le périmètre prévu. Les nouvelles routes de
lecture exigent le secret de passerelle, la session privée, le jeton et l'origine
HTTPS. Aucune note, clé du lien ou configuration privée n'est publiée.

## Vérifications réalisées

La [CI de la version publiée](https://github.com/Louisgsln/Immortal-Trading/actions/runs/39317266615)
réussit **5 783 tests Python 3.14** et le job JavaScript. Les autres versions Python
et le job Docker hébergé restent en cours au relevé de préparation.

En local : 319 tests Dashboard passent, puis 56 vérifications ciblées de la
version finale et 20 contrôles de contrat. Ces groupes se recouvrent et ne se
cumulent pas. Trente et un nouveaux cas Python couvrent notamment le chargement
concurrent, les refus d'accès, le maintien de la liste entière et la reprise
après erreur. Les **53 tests JavaScript** passent. Ruff, le format sur 363 fichiers
et Mypy sur 133 modules passent.

Le parcours Chromium à **390 × 844**, exclusivement sur données synthétiques,
vérifie l'ouverture, le chargement complet, les filtres, les souhaits, une note,
le passage en « Postulé » et l'affichage arrêté/actif sans rechargement.
Aucune erreur de page ou de requête. Les offres et le curseur Telegram de cet
essai sont identiques avant/après. Le premier écran arrive en **0,252 seconde**
dans cet environnement ; ce chiffre n'est pas une mesure de production.

La nouvelle image Docker locale passe le contrat de **93 contrôles / huit
modules** et l'essai de restauration avec **onze tables identiques**, avec
512 Mio, un CPU, réseau désactivé, système de fichiers en lecture seule et
utilisateur 10001. Sur le VPS, le wheel est construit, installé sans mode
éditable, puis vérifié avec le même contrat et l'essai local de restauration.
Ce dernier contrôle ne remplace pas la validation Docker du VPS encore prévue.

## Lot 181 : les incidents ne sont pas tous clos

Deux passages publics séparés récupèrent les mêmes quatre fiches SMBC, avec
des champs métier identiques et sans lacune : environ cinquante secondes et
26 requêtes à chaque fois. Cela confirme le collecteur sur ces essais, sans
prétendre supprimer les futurs délais du portail ni importer ces essais.

U.S. Bank fournit d'abord **19 fiches complètes** parmi 511 résultats, puis une
seconde traversée échoue sur une répétition de page Workday, même après la reprise
bornée existante. L'incohérence reste signalée et **aucun import incomplet n'est
accepté**. Les anciennes données demeurent. [Audit daté](SOURCE-AUDIT-LOT181.json).
Nomura campus reste en attente de l'intervention humaine choisie par le
propriétaire. Aucun ajout fictif de source, aucune donnée inventée.

## Installation préparée et limites

Le précontrôle du VPS vérifie les huit fichiers concernés, le profil inchangé,
le paquet installé et les scripts préparés. L'installation prévoit une sauvegarde
vérifiée, une comparaison des données complètes sur copie restaurée, puis le
remplacement du seul Dashboard. Les workers radar/Telegram/sauvegardes et la
passerelle HTTPS doivent garder leurs conteneurs. Un échec restaure uniquement
le code et l'image précédents, jamais la base active. Les quinze contrôles de
conservation restent exigés après installation.

Le chantier 176 reste ouvert : cette livraison améliore la première réponse
et la navigation mobile, mais transfère encore l'ensemble des descriptions.
L'affichage utilisable avec toutes les données en moins de cinq secondes sur
OVH reste à mesurer puis à obtenir. Le prochain jalon porte sur les détails
chargés à la demande, avec des filtres et compteurs globaux exacts.
