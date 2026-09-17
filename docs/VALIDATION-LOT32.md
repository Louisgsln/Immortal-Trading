# Lot 32 — Actualisation Greenhouse et comparaison des champs

Travaux du **17 septembre 2026**, avec deux sous-agents : enrichissement de l'aperçu
et audit qualité hors réseau. L'agent principal a capturé les catalogues, vérifié
l'offre supplémentaire, sauvegardé, répété l'import puis actualisé les données.

## Résultat métier

**Une nouvelle offre importée : [DRW Floor Trader](https://job-boards.greenhouse.io/drweng/jobs/8207750),
Chicago, score actuel 79.** L'employeur indique temps plein, catégorie Campus,
début cible été 2027 et diplôme attendu entre décembre 2026 et juin 2027.
L'expérience préalable en trading est facultative. Aucune deadline publiée.

La première publication indiquée est le **16 septembre 2026 à 22:00:49 UTC** ;
la détection locale intervient le 17 septembre. L'ID stocké est
`bc7cb69d-4865-4a23-a82e-39bdc356d48e`, distinct des identifiants temporaires des
aperçus et de la répétition.

| Source | Catalogue public | Offres retenues | Nouvelles |
| --- | ---: | ---: | ---: |
| IMC | 174 | 26 | 0 |
| DRW | 154 | 27 | 1 |
| Flow Traders | 40 | 10 | 0 |
| Jump Trading | 108 | 25 | 0 |
| XTX Markets | 10 | 1 | 0 |
| **Total** | **486** | **89** | **1** |

Six requêtes réussies, règles robots comprises, avec espacement de deux secondes
et aucun retry interne. Une première tentative de transport dans le réseau
restreint avait échoué ; la capture publique autorisée n'a contourné aucun refus.
Les cinq réponses ont été archivées avec URL, date, taille et SHA-256.

Les captures ont ensuite alimenté l'aperçu et les deux imports locaux, avec zéro
requête supplémentaire. Les compteurs réseau du scan d'import valent donc zéro ;
les six requêtes réelles figurent dans le manifeste de capture. La configuration
et les empreintes des captures ont été revérifiées à chaque étape, ainsi qu'une
ancienneté de capture inférieure à trente minutes.

## Préparation et préservation

- Aperçu sur snapshot : cinq succès, 89 offres, un ajout, aucune modification de
  contenu, fermeture ou alerte.
- Sauvegarde vérifiée `data/backups/lot32-before-greenhouse.zip`, puis restauration
  dans `data/discovery/lot32/rehearsal.db`. Onze tables initialement identiques.
- Répétition puis import réel donnant les mêmes compteurs. Les sources sont
  partielles : aucune fermeture déduite d'une annonce absente.
- **813 suivis de candidature précédents intégralement préservés**. Un suivi
  local `New` créé pour l'offre supplémentaire, sans candidature envoyée.
- Parmi les offres antérieures, **88 dates d'observation/statuts is_new actualisés**,
  sans autre changement de payload ; **725 offres intégralement inchangées**.
- Historiques antérieurs conservés ; un événement `new`, un score et un scan
  ajoutés. Alertes, historique d'alertes et historique de candidatures inchangés.
- Intégrité SQLite valide et aucune erreur de relation. Un nouvel aperçu après
  import propose zéro changement et conserve les onze tables.

Base finale : **814 offres, 812 actives, 164 scores actifs ≥70 et 250 ≥55**, 46 scans
métier, aucune alerte. CSV et dashboard exportés à nouveau : les deux contiennent
l'offre ajoutée. Pas de nouvelle inspection visuelle de l'interface.

## Fonction livrée et audit qualité

`scan --dry-run` ajoute `changed_fields` à chaque événement : liste déterministe
de noms de champs métier modifiés, sans valeur de description ni note personnelle.
Les dates techniques sont exclues. Une nouvelle offre a une liste vide ; les
événements successifs comparent chacun leur état précédent. Le champ complète
le rapport existant, sans modifier les règles de création de l'historique.
Guide : [SCAN-PREVIEW.md](SCAN-PREVIEW.md).

L'[audit qualité](GREENHOUSE-QUALITY-LOT32.md) examine les 88 offres antérieures :
22 titres Graduate/Junior/Intern/Analyst, dont 12 scores nuls. Onze sont des stages
correctement exclus et le dernier est un Research Analyst demandant 3–6 ans.
Aucun titre Graduate injustement exclu n'a été identifié dans ce périmètre.

La nouvelle DRW apporte un cas concret pour la suite : sa catégorie Campus et
ses critères de diplôme ne donnent pas encore d'indice junior structuré, d'où
5/20 sur cette composante. Le score de 79 est celui du barème actuel, pas une
certification d'éligibilité ; les actifs relevés dans la présentation générale
DRW ne prouvent pas la spécialisation exacte du poste. Une correction étroite est
proposée, avec les stages DRW marqués Full-time comme contre-exemples. Les rôles
techniques hybrides IMC/Jump restent ambigus ; leurs exclusions sont conservées.

## Validation et preuves

- **1 888 tests réussis**, soit quatre nouveaux ; couverture Python **96 %**.
- Tests spécifiques : description seule, métadonnées seules, changements
  successifs et explication de score modifiée à total constant ; aucune fuite de
  notes, payload brut ou description dans le rapport.
- Ruff : 148 fichiers conformes ; mypy : 61 fichiers sans erreur.
- Paquet reconstruit hors réseau depuis `uv.lock`, suite complète sur installation
  non éditable. Aucune dépendance, migration ou configuration métier modifiée.

Preuves locales sous `data/discovery/lot32/` : `before.json`, `capture-restricted/`,
`capture-live/manifest.json` et cinq catalogues, `preview.json`, `rehearsal.json`,
`import.json`, `preservation.json`, `post-import-preview.json`, `quality-audit.json`,
`test-results.xml` et `test-results.txt`. Le script ponctuel `workflow.py` documente
la capture et le replay ; ces artefacts de travail sont exclus du suivi Git.

Aucun watcher, notification, envoi de candidature ou déploiement lancé. Docker/VPS
et la copie distante des sauvegardes restent à valider sur un environnement équipé.
