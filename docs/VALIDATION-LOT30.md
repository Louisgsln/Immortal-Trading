# Lot 30 — Filtres Workday et mesures ciblées Citi

Travaux du **17 septembre 2026**, avec deux sous-agents : options et requêtes du
collecteur, puis sonde et documentation. L'agent principal a vérifié les filtres
publics, effectué les mesures, ajouté un test d'intégration du scanner et validé
l'ensemble.

## Fonction livrée

- `WorkdayOptions.applied_facets` transmet des filtres explicites au champ public
  CXS `appliedFacets`. Sans option, les requêtes gardent leur comportement précédent.
- Validation stricte : au plus cinq clés ASCII, de 1 à 64 caractères ; de une à dix
  valeurs textuelles uniques par clé, de 128 caractères maximum, sans caractères
  de contrôle. Les types incorrects et listes vides sont refusés.
- Configuration, options et corps de chaque requête possèdent leurs propres
  copies du filtre. La sonde peut remplacer le périmètre uniquement en mémoire.
- `--facet KEY=VALUE` répétable ; plan et rapport conservent les valeurs réellement
  envoyées. Le mode par défaut reste hors réseau.
- Budgets inchangés : 200 résultats par recherche, 12 détails supplémentaires,
  180 secondes par sonde, délai HTTP de 20 secondes, aucun retry interne.
- Les recherches restent partielles. Un résultat filtré vide ne ferme pas les
  offres précédemment connues, même avec un seuil de fermeture d'un seul scan.

La validation des facettes est syntaxique. Elle n'atteste ni leur acceptation par
un serveur donné, ni le niveau junior des postes. Les valeurs doivent provenir
du portail concerné. Guide : [WORKDAY-QUERY-PROBE.md](WORKDAY-QUERY-PROBE.md).

## Mesure réelle

La page publique Citi expose les catégories `Institutional Trading` et
`Management Development Programs`. Leurs identifiants et comptes ont été archivés
avant de les utiliser. Les totaux filtrés `repo` concordent avec ces comptes.

| Catégorie | Recherche | Résultats paginés | Titres retenus | Inconnus |
| --- | --- | ---: | ---: | ---: |
| Institutional Trading | repo | 47 | 14 | 0 |
| Institutional Trading | securities finance | 56 | 23 | 0 |
| Management Development Programs | repo | 59 | 0 | 0 |
| Management Development Programs | securities finance | 1 | 1 | 0 |

Les quatre recherches représentent **26 chemins distincts déjà connus**. Aucun
détail n'a été relu, puisque la sonde ne lit que les chemins inconnus. Ce résultat
ne garantit pas l'exhaustivité de Citi, la fraîcheur des fiches connues ou la
couverture complète des programmes juniors. Le filtre local de titres continue
de s'appliquer.

Une première tentative de découverte a échoué dans le réseau restreint ; les
lectures publiques suivantes ont respecté robots.txt et l'espacement configuré.
Les mesures réussies comptent 14 requêtes, règles robots comprises, plus une
tentative de transport échouée. Aucun refus du site n'a été contourné.

La configuration active reste `search_terms: [trading]`, sans facette. Aucun gain
de couverture n'a été démontré dans ces périmètres pour justifier des requêtes
supplémentaires à chaque scan. Détails et limites :
[CITI-FACET-SCOPE-LOT30.md](CITI-FACET-SCOPE-LOT30.md).

## Préservation et tests

- **Onze tables identiques avant/après**, vérifiées par compteurs et SHA-256.
  Intégrité SQLite valide et aucune erreur de relation.
- Toujours **813 offres, 811 actives, 163 scores actifs ≥70 et 249 ≥55** ; 45 scans
  métier. Aucune candidature, alerte ou historique modifié.
- **1 849 tests réussis**, soit **70 nouveaux**, couverture Python **96 %**.
- 51 tests de facettes, 18 nouveaux tests de sonde et un scénario d'intégration
  vérifiant la préservation des offres et candidatures avec un résultat filtré vide.
- Ruff : **145 fichiers** conformes ; mypy : **60 fichiers**, sans erreur.
- Paquet reconstruit hors réseau depuis `uv.lock`, suite complète sur une
  installation non éditable. Aucune dépendance ni migration ajoutée.

Preuves sous `data/discovery/lot30/` : `before.json`, `preservation.json`,
`discovery/`, `discovery-live/`, `plan/`, `filtered-live/`, `programmes-live/`,
`test-results.xml` et `test-results.txt`. Les manifestes des sondes et l'empreinte
de la réponse de découverte ont été revérifiés. Ces artefacts sont ignorés par Git.

Les sources synchronisées, la configuration opérationnelle et les exports métier
n'ont pas été modifiés. Aucune notification, candidature, surveillance ou import
n'a été lancé. L'interface est inchangée ; pas de nouvelle inspection visuelle.
Docker/VPS et la copie distante des sauvegardes restent à valider séparément.
