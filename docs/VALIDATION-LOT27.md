# Lot 27 — Intégrité Workday et sonde Citi

Validation effectuée le **17 septembre 2026**. Trois sous-agents ont traité le
collecteur, la sonde d'audit et la disponibilité du runtime ; intégration,
mesures réseau et validation globale par l'agent principal.

## Résultat

Le collecteur Workday refuse désormais toute la collecte si une fiche détaillée
ne correspond plus au titre sélectionné, contient des champs consommés mal typés,
ou partage son identifiant stable avec un autre chemin. Les différences de
présentation des titres restent acceptées. Aucun lien arbitraire n'est imposé
entre l'identifiant stable, la réquisition et le suffixe d'URL.

Trois tests d'intégration simulent une première fiche valide, puis une seconde
invalide : aucune offre, candidature, alerte ni aucun historique métier n'est
modifié. Seuls l'état d'échec de la source et les métriques du scan sont enregistrés.
La reprise suivante réussit, conserve le suivi de candidature et ne ferme pas
les offres absentes de cette recherche partielle.

Les 16 couples recherche/détail archivés ont été rejoués avec des résultats
strictement identiques. Les 125 offres Workday en base ne conservent pas ces
couples bruts et ne permettent pas ce même contrôle. Détails et empreintes dans
[WORKDAY-INTEGRITY-LOT27.md](WORKDAY-INTEGRITY-LOT27.md).

## Mesure réelle Citi

La [sonde](WORKDAY-QUERY-PROBE.md) fonctionne sans réseau par défaut. Le mode réseau
est explicite : au plus deux termes, 200 résultats par recherche, 12 détails
supplémentaires, 180 secondes, délai HTTP de 20 secondes, aucun retry interne et
intervalle minimal de deux secondes. Elle lit SQLite en lecture seule et n'importe rien.

| Exécution | Résultat | Requêtes comptées | Détails lus |
| --- | --- | ---: | ---: |
| Première tentative dans le réseau restreint | Erreur de transport | 1 | 0 |
| Nouvelle tentative autorisée, `repo` en premier | Plafond de 200 résultats dépassé | 2 | 0 |
| Mesure séparée de `securities finance` | Plafond de 200 résultats dépassé | 2 | 0 |

Les deux accès autorisés ont chacun lu les règles robots puis soumis la première
page de recherche. Les totaux dépassaient le plafond avant pagination ; leur
valeur exacte n'a pas été conservée par le collecteur. La seconde recherche a été
exécutée séparément parce que le dépassement de la première arrête la sonde entière.
Les limites n'ont pas été relevées.

Ces résultats ne mesurent ni le nombre de postes retenus ni le gain de couverture.
Ils ne démontrent pas l'absence d'offres supplémentaires. Les recherches restent
incomplètes ; `search_terms: [trading]` et le cache désactivé sont conservés.
La référence locale comprend 57 chemins Citi connus. Son dernier horodatage est
individuel et ne reconstitue pas un lot complet de scan.

Preuves locales sous `data/discovery/lot27/` : `plan/`, `live/`, `live-retry/`,
`securities-finance/`. Chaque dossier conserve son plan et son manifeste ; les
tentatives réseau ajoutent rapport et détails. Toutes les tailles et empreintes
SHA-256 des manifestes ont été vérifiées. Aucun fichier de preuve n'a été écrasé.

## Base et validation

- Contenu exact des **11 tables** identique avant/après, vérifié par compteurs et
  SHA-256 ; intégrité SQLite `ok`, aucune erreur de relation.
- **813 offres, 811 actives**, toujours 45 scans métier ; aucune candidature,
  notification, collecte importée ou surveillance lancée.
- **1 609 tests réussis**, soit 92 nouveaux ; couverture Python **96 %**.
- Ruff : **135 fichiers** conformes ; mypy : **57 fichiers**, sans erreur.
- Paquet reconstruit hors réseau depuis `uv.lock`, suite complète exécutée sur
  une installation non éditable. Aucune dépendance ni migration ajoutée.
- Après harmonisation des fins de ligne, paquet final reconstruit et **142 tests
  Workday/sonde/scanner** réexécutés avec succès ; module installé identique au source.

Preuves : `before.json`, `preservation.json`, `test-results.xml` et
`test-results.txt` sous `data/discovery/lot27/`. Ces artefacts sont ignorés par Git.
Les sources synchronisées et la configuration opérationnelle n'ont pas été modifiées.
L'interface et ses exports n'ont pas changé ; aucune nouvelle inspection visuelle
n'est annoncée.

## Runtime et suite

Docker et Podman sont absents du PATH. `wsl.exe` existe, mais les commandes de
statut confirment que WSL n'est pas installé. Aucun runtime n'a été installé ou
activé. La validation Docker/VPS reste à réaliser sur un hôte équipé ; preuves
dans [RUNTIME-CHECK-LOT27.md](RUNTIME-CHECK-LOT27.md).

Prochaines pistes : identifier un filtre public Citi réellement plus étroit avant
de relancer une mesure, puis poursuivre les qualifications alternatives et les
portails early careers. Aucun élargissement automatique de la collecte n'est justifié
par cette mesure incomplète.
