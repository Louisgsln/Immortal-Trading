# Lot 40 — Provenance et cadre de l’expérience Jump

Travaux du **17 septembre 2026**, avec trois sous-agents : modèle/collecteur,
présentation, audit et régressions indépendantes. L’agent principal a intégré
la correction contrôlée, le stockage, les mesures et les validations.

## Résultat visible

La fiche Jump de Hong Kong demandait cinq ans de pratique du codage **en industrie
ou dans le monde académique**. Cette durée était stockée comme un minimum
professionnel de cinq ans, puis utilisée par la règle d’exclusion d’expérience.

Le dashboard conserve maintenant la preuve de cinq ans, son cadre, l’extrait exact
et la mention **« Déduit de la description »**. Il affiche **« Minimum professionnel
non reconnu »** et place l’offre dans le filtre des minima non reconnus.
La règle ne transforme pas cette pratique mixte en durée d’emploi.

| Offre Jump / référence employeur | Avant | Après |
| --- | --- | --- |
| Quantitative Developer, Hong Kong — `6172858` | Minimum 5, sans provenance typée | Minimum professionnel inconnu ; preuve de pratique 5 ans, industrie ou académie ; junior 0→5, exclusion d’expérience retirée. |
| Quantitative Developer, New York ou Chicago — `7767735` | Minimum 2, sans provenance typée | Minimum 2 conservé ; preuve professionnelle et extrait ajoutés. |

**Les deux scores restent nuls**, car leur exclusion métier indépendante est
préservée. Le total d’aucune offre ne change : **812 actives, 240 pertinentes,
161 prioritaires**. Parmi les actives, les catégories d’expérience deviennent
**71 minima 0–2 ans, 184 >2 ans et 557 non reconnus**.

L’[audit indépendant](EXPERIENCE-PROVENANCE-LOT40.md) relie les deux corrections aux
captures employeur, aux descriptions conservées et à leur provenance. La référence
`7767735` est bien New York ou Chicago ; elle ne doit pas être confondue avec les
autres offres Jump de même titre en Asie.

## Modèle et collecte

- `ExperienceEvidence` conserve durée, cadre, origine, méthode et extrait exact.
  Une liste vide par défaut préserve la lecture des anciens JSON ; aucune migration
  SQLite n’est nécessaire, ce champ appartenant au payload de l’offre.
- Le collecteur Jump distingue une preuve professionnelle, mixte industrie/académie,
  ou de cadre non précisé. Seules les preuves explicitement professionnelles
  alimentent son champ `minimum_experience_years`.
- Les changements de preuve sont historisés pendant les collectes et nommés dans
  leur aperçu, même lorsque le minimum numérique et le score restent identiques.
- Les anciens payloads ne sont pas corrigés à leur lecture. La correction hors
  collecte vérifie d’abord que la valeur historique est reproductible depuis la
  phrase auditée, refuse les valeurs ou preuves inattendues, puis prépare une copie.
- Le stockage n’accepte que les champs dérivés d’expérience et la décomposition
  associée. L’opération est enregistrée comme recalcul, sans changer la fraîcheur
  de la source, sous verrou et transaction pris par l’appelant.

La provenance des autres collecteurs reste à auditer. Une ancienne valeur sans
preuve typée n’est pas déclarée professionnelle ni publiée directement par
l’employeur par cette extension. Le cas Jane Street HR et une interprétation
générale des alternatives académiques restent hors périmètre.

## Correction de la base locale

L’impact approuvé porte le SHA-256
`eafade17d4816165a3c8731995989f6b9a9fa594141d52116aaefbaf75c8b287`.
La revue a rejoué les 814 offres, confronté les deux preuves aux données brutes
et vérifié les onze empreintes de tables avant application.

La sauvegarde `data/backups/lot40-before-experience-provenance.zip` a été restaurée
dans une base distincte et la correction répétée avant son application réelle.
**Deux lignes d’offres changent**, une seule décomposition de score change,
**812 lignes restent identiques**. Deux versions et deux entrées d’historique
de score sont ajoutées. Huit autres tables sont inchangées, dont candidatures,
alertes et état des sources. Descriptions, contrats et dates restent identiques.
La correction et le recalcul ordinaire sont ensuite sans effet au deuxième passage.

Les 814 fiches HTML et lignes CSV ont été comparées à la base ; les indicateurs
et preuves du HTML correspondent au nouveau modèle. L’export et le serveur local
ont été actualisés.

## Tests et interface

**2 438 tests réussis**, dont 96 nouveaux, sur le paquet installé non éditable
sous Windows Python 3.14 ; **96 % de couverture**. Ruff/format passent sur
174 fichiers et mypy sur 68 fichiers, dont quatre scripts.

Les parcours Edge vérifient l’export et le serveur local : filtres, seuils,
preuve mixte, minimum professionnel distinct, preuve professionnelle de deux ans,
extraits exacts et exclusions métier préservées. La vue mobile à 390 pixels
est vérifiée sans débordement horizontal. Sept variantes synthétiques couvrent
les preuves absentes ou mal formées et un extrait contenant une tentative d’injection
HTML : affichage en texte, aucun élément injecté ni script exécuté.

Les sélecteurs du test navigateur ont été précisés après deux ambiguïtés : la preuve
est visible à la fois dans la liste et le détail, et plusieurs postes partagent
le même titre. La vérification finale cible le détail et la localisation exacte ;
elle passe sans erreur JavaScript.

CI réussie pour le commit `5da14382c7d54c2898be419e2dd134f6cbc7e39c` :
[exécution du lot 40](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35210389365).
Les versions Python **3.11 à 3.14** passent chacune les **2 438 tests**, avec
96 % de couverture. Le build Docker, l’entrée de commande et la restauration
passent également : UID 10001, réseau coupé, **onze tables restaurées identiques**.
Logs copiés dans les preuves locales et rapports disponibles dans la CI.
WSL reste à activer sur le poste Windows pour l’exploitation Docker locale ;
la validation conteneur de ce lot est réalisée sous Linux en CI.

## Preuves locales

Dans `data/discovery/lot40/`, hors Git : référence initiale, rejeu des captures,
impact, revue indépendante, sauvegarde restaurée, application, second recalcul,
résultats pytest/JUnit, vérifications des exports, parcours Edge et captures
ordinateur/mobile. Les scripts de mesure et de correction y sont conservés.
