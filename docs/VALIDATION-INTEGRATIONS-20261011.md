# Lots 141-A et 143-A — intégrations installées le 11 octobre 2026

**79 sources / 67 employeurs / 78 catalogues distincts**, contre 75 / 65 / 74.
Au relevé `2026-10-11T15:34:40.063998+00:00` : **72/79 à jour** ; [liste complète](RADAR-SOURCES-20261011.md).
[Preuves publiques](DELIVERY-INTEGRATIONS-20261011.json) ; [carnet](TASK-BOARD.md).

## Lot 141-A — banques françaises et campus

Rothschild étudiants : catalogue public entier de 60 programmes, pages de 50 puis 10,
contrôle de la première page avant les détails. Six fiches de marchés/Redburn retenues.
Deux formats officiels Tal.net vérifiés, identité numérique employeur, titres et descriptions concordants.
Les programmes M&A hors filtres restent écartés. L'offre GMS Francfort porte officiellement
« Long Term Internship » mais annonce trois mois : elle n'est pas transformée en stage long de 6–12 mois.

BNP campus : catalogue officiel anglais Trainee / Internship, recherches `trading` et `structuring`,
contrat de stage contrôlé sur chaque carte et chaque fiche. Deux fiches vérifiées ; **14 lacunes explicites**.
Les fiches refusées restent dans les lacunes ; aucun refus n'est traité comme une offre complète.
Une erreur de pagination ou l'indisponibilité de toutes les fiches interrompt l'import.
Le site français général reste HTTP 403 ; la recherche anglaise générale échoue à la page 17,
la recherche quantitative stages à la page 3. Ces périmètres restent des tâches ouvertes.

## Lot 143-A — fonds

Millennium professionnels : portail officiel distinct du campus, collecteur Eightfold commun aux deux
avec origines et paramètres séparés. Pages de dix, première page recontrôlée, titre, référence ATS et
JobPosting concordants. Les liens comportant des caractères Unicode sont ramenés à l'identifiant stable.
Le paramètre campus ne peut pas être injecté dans une URL professionnelle.

Brevan Howard : le catalogue Phenom officiel relie le tenant Workday `brevanhoward/BH_ExternalCareers`.
CXS public et descriptions intégrales, quatre recherches ciblées, 17 fiches retenues.
Le **3–6 Month Off Cycle Internship**, Genève/Londres, est collecté ; son année de début reste inconnue.
La conversion possible vers un Graduate Program 2028 et la date de graduation ne prouvent pas un début 2027.
Son intitulé générique reste à 0 : qualification des missions au lot 133, sans inflation arbitraire du score.
Les Summer restent hors des alertes de stages.

## Résultats et limites

| Source | Fiches retenues | Score ≥70 | Stages 2027 admissibles ≥70 | État |
|---|---:|---:|---:|---|
| `rothschild_campus` | 6 | 1 | 0 | À jour |
| `millennium_professionals` | 46 | 2 | 0 | À jour |
| `brevan_howard` | 17 | 1 | 0 | À jour |
| `bnp_campus` | 2 | 1 | 0 | Partielle |

**71 associations de sources, 70 identités nouvelles ; base 1 434 → 1 504**, avec déduplication BNP.
Aucun nouveau stage de ces quatre sources n'a encore une admissibilité 2027 ≥70 entièrement confirmée.
Les scores élevés comprennent des postes professionnels. La qualification métier de Rothschild 539 (GMS/advisory,
78/100) est à auditer au lot 133 ; le format non confirmé le garde hors des alertes de stage.
Le Dashboard affiche 38 fiches satisfaisant les critères stage/score actuels ; fraîcheur,
échéance, statut de candidature et historique continuent de conditionner chaque envoi.
Ces imports initiaux ne sont pas des publications récentes ni un débit hebdomadaire attendu.

## Installation et conservation

Image : `immortal-trading:lot140-integrations-20261011`. Code : `e70d0cd676d3a6709d96fd71beafac907bf7a815`.
Profil final public SHA-256 : `12b07d77fccc9d68374f08a9ae3e9df758d1efc2a262659e66de4f931d26c963`.
Cadence des quatre ajouts : 30 minutes ; requêtes espacées de deux secondes au minimum,
avec règles robots et délais employeur. Standard Chartered interdit son endpoint de recherche dans robots.txt :
pas d'activation. Lloyds, NatWest, BPCE/Natixis, JPMorgan campus, Balyasny, Rokos et les autres fonds restent au carnet.

Simulation sur copie avec notifier interdit : zéro appel et zéro nouvelle alerte.
Sauvegarde ZIP vérifiée avant installation ; schema SQLite 4 et inode conservés.
Toutes les anciennes identités, candidatures, lignes de suivi, alertes envoyées et historiques conservés.
Curseur Telegram monotone, liaison propriétaire et préférences du digest conservés.
Import réel silencieux : zéro alerte créée ; 48 alertes envoyées et leur historique conservés.
Aucun message Telegram de test envoyé pour cette livraison.

Radar, listener, sauvegardes et Dashboard utilisent la même image ; cinq services Docker actifs,
quatre unités systemd actives et activées. Même lien HTTPS privé éditable ; certificat valide,
86 contrôles et sept modules du Dashboard vérifiés. Réponse mesurée : 16.222 s.
Accès public 404, fichier privé 404, POST page privée 405, API sans CSRF 403.
Le réglage de cadence a temporairement rendu la configuration illisible sous umask restrictif :
permissions publiques 0644 restaurées, services relancés et conservation revérifiée.
La publication atomique impose désormais explicitement fchmod pour préserver le mode.
Les compteurs de redémarrage sont stables ; la liste de 33 commandes bloquées RDC, dont sudo, est rétablie.

## Validation automatisée

41 nouveaux tests : pagination complète, changements pendant lecture, URL et identités,
contrats BNP, lacunes 403/404, échec complet, authentification, années de conversion et exclusion Summer.
Ruff et mypy passent ; 213 tests ciblés passent, couverture des trois collecteurs 92 %.
CI fonctionnelle : [38150072028](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38150072028),
5 294 tests par version Python 3.11–3.14, 34 tests Node et contrôle du conteneur.
Les six jobs sont réussis, couverture Python 96 %. Les preuves consignent le résultat et les conteneurs stabilisés.

## Reprises et prochaines tâches

141-B : résoudre les 14 fiches BNP et les recherches refusées ; BPCE/Natixis public à développer.
143-B : établir le vrai catalogue Balyasny, puis Rokos et les accès publics Citadel/Two Sigma.
140 : Standard Chartered robots interdit ; Lloyds à raccorder, NatWest HTTP 403.
147 : diagnostiquer Goldman campus (données de rôle incohérentes), Point72 (timeout)
et Morgan Stanley campus (échec récent). Ne pas supprimer les historiques pour masquer ces erreurs.
133–134 : qualifier les missions et débuts Brevan, Rothschild et les témoins déjà listés.
