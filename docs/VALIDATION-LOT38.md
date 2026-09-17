# Lot 38 — Stages explicites dans les descriptions Jane Street

Travaux du **17 septembre 2026**, avec trois sous-agents : audit des stages et
tests indépendants, implémentation, audit des exigences d’expérience restantes.
L’agent principal a mesuré les impacts, vérifié le paquet installé et appliqué
le recalcul après sauvegarde et répétition sur une copie restaurée.

## Problème et correction

Certaines offres Jane Street portent le titre `Quantitative Trader` ou
`Sales and Trading`, sans contrat structuré, alors que leur description présente
explicitement un stage. Elles pouvaient donc apparaître dans le classement junior
malgré l’exclusion des stages prévue par le radar.

Le helper `explicit_jane_street_internship` reconnaît les formulations directes
adressées au candidat : `As an intern, you…`, `As a … intern, you…`,
`During the internship, you…`, `Over the course of your internship, you…`
et `You'll spend the bulk of your internship…`, avec un temps présent ou futur.
Il ajoute le motif `description explicitly identifies a Jane Street internship`.

La règle est bornée à la source officielle `jane_street` et à l’entreprise
normalisée `jane street`. Elle conserve la ponctuation, écarte les citations,
conditions, négations et contextes passés reconnus. Elle ne modifie pas les
contrats source et ne lève aucune autre exclusion.

Ce périmètre conservateur ne prétend pas reconnaître toutes les formulations de
stage. Les descriptions contradictoires d’autres employeurs et les titres avec
homoglyphes restent hors périmètre. Voir l’[audit indépendant](INTERNSHIP-AUDIT-LOT38.md).

## Mesure sur le corpus local

| Mesure | Avant | Après recalcul |
| --- | ---: | ---: |
| Offres conservées / actives | 814 / 812 | 814 / 812 |
| Actives pertinentes, score ≥55 | 246 | 240 |
| Actives prioritaires, score ≥70 | 161 | 161 |

Les **45 fiches** ciblées correspondent exactement aux identifiants de l’audit,
dont 43 actives. Six scores totaux changent : trois Quantitative Trader passent
de **65 à 0**, et trois Sales and Trading de **61, 57 et 57 à 0**.
Les 39 autres étaient déjà à zéro ; elles gagnent un motif indépendant de stage.

Le Trader Crypto de Jump reste à **71** : son texte évoque l’histoire de
l’entreprise. Le GEM Trader Analyst de Deutsche Bank reste à **90** : les stages
sont une expérience antérieure recevable. Les minima d’expérience et leurs
catégories restent inchangés.

## Autre audit livré

L’[audit des formulations d’expérience avec « in »](EXPERIENCE-IN-AUDIT-LOT38.md)
documente 15 offres et sept qualifications certaines encore mal reconnues.
Il prépare une correction future, sans modifier le parseur dans ce lot.
Les durées contractuelles, alternatives académiques et parcours indicatifs sont
distingués des exigences professionnelles.

## Validation

**2 229 tests passent** sur le paquet installé non éditable sous Windows
Python 3.14, avec **96 % de couverture**. Les 77 nouveaux tests comprennent
24 régressions indépendantes. Ruff, format (165 fichiers) et mypy (66 fichiers,
dont quatre scripts) sont conformes.

La revue indépendante a rejoué les 814 offres avant application et vérifié les
identifiants, les scores précédents, les hashes des descriptions et l’ajout du
seul motif d’exclusion. L’impact approuvé porte le SHA-256
`e90164c9052bc38a04beac919711ee1b9f0001f71344751bf6acd79021369d7c`.

La sauvegarde locale `data/backups/lot38-before-explicit-internships.zip` a été
restaurée dans une base distincte avant répétition du recalcul. La même opération
a ensuite été appliquée à la base active : **45 versions et 45 entrées d’historique
de score ajoutées**, huit autres tables identiques, 769 lignes d’offres inchangées.
Descriptions, contrats et dates de collecte sont préservés. Un deuxième passage
ne produit aucun changement.

Les 814 lignes CSV et les 814 fiches du HTML ont été comparées à la base. Les
parcours Edge de l’export et du serveur local vérifient les seuils 55/70, les trois
Sales and Trading exclus et leur motif, le Crypto Trader à 71 et les deux GEM
Trader Analyst à 90. Aucune erreur JavaScript ni modification de candidature.
Le script de vérification initial attendait une seule fiche GEM ; il a été corrigé
après vérification des deux annonces existantes, puis rejoué avec succès.

La validation GitHub du commit `cf23a1789c0ae430c026714c7f57f44a8626d392`
est réussie : [exécution du lot 38](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35207223955).
Les quatre versions Python 3.11 à 3.14 passent chacune les **2 229 tests**, avec
96 % de couverture. Le build Docker, l’entrée de commande et la reprise passent
également : UID 10001, réseau coupé, **onze tables restaurées identiques** et
nettoyage du conteneur et du volume synthétiques. Les logs sont conservés localement
et les rapports de CI sont disponibles dans l’exécution liée.

Docker Linux est vérifié en CI ; WSL reste à activer sur le poste Windows avant
l’exploitation locale sous Docker. Aucun nouveau contrôle de l’hôte cible n’est
revendiqué dans ce lot.

Les preuves locales sont conservées dans `data/discovery/lot38/`, hors Git :
snapshots initiaux, audits, impact et revue indépendante, répétition et application,
second recalcul, résultats pytest/JUnit, contrôles des exports, parcours navigateur
et captures. Les scripts de mesure, de recalcul et de vérification y sont conservés.
Le dépôt public contient les sources, les tests et les rapports d’audit.
