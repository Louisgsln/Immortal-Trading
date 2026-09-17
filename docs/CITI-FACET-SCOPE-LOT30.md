# Citi — mesure de recherches filtrées, lot 30

## Résultat

Les recherches `repo` et `securities finance`, restées trop larges au lot 27,
ont été entièrement paginées dans deux catégories publiques du portail Citi.
Les quatre recherches retiennent **26 chemins distincts déjà connus** du radar,
sans chemin supplémentaire selon les filtres de titres actuels.

Cela ne démontre pas l'exhaustivité mondiale de Citi. La configuration active
reste `search_terms: [trading]`, sans facette : aucun de ces périmètres plus étroits
ne remplace silencieusement la collecte existante.

## Découverte et provenance

Le 17 septembre 2026, une première page de recherche publique `repo` a été lue via
le client HTTP du projet, depuis le [portail Citi](https://citi.wd5.myworkdayjobs.com/2).
L'endpoint est `https://citi.wd5.myworkdayjobs.com/wday/cxs/citi/2/jobs`, avec
`appliedFacets: {}`, `limit: 20`, `offset: 0` et `searchText: repo`.

Le serveur annonce **2 000** résultats ; ce chiffre n'est pas présenté comme
un décompte exhaustif. La page expose notamment la facette `jobFamilyGroup`,
libellée `Job Category`, avec ces identifiants :

| Catégorie | Identifiant public | Compte annoncé pour `repo` |
| --- | --- | ---: |
| Institutional Trading | `e32326e1708d0170affb000d120106c1` | 47 |
| Management Development Programs | `e32326e1708d01eb680bf90c1201e8c0` | 59 |

Les identifiants ont été repris de cette réponse, sans dérivation à partir des
libellés. La réponse et son empreinte sont conservées sous
`data/discovery/lot30/discovery-live/`. SHA-256 de `response.json` :
`5f1e701da7ddf76b6c203c02e694804871caa4e269bb2296043ede732b61712b`.

Une première tentative dans le réseau restreint a échoué en transport ; elle est
conservée dans `discovery/`. La lecture publique autorisée a ensuite respecté
robots.txt et l'intervalle de deux secondes. Aucun mécanisme de contournement
d'un refus du site n'a été utilisé.

## Mesures

| Catégorie | Terme | Résultats paginés | Titres retenus | Chemins inconnus |
| --- | --- | ---: | ---: | ---: |
| Institutional Trading | `repo` | 47 | 14 | 0 |
| Institutional Trading | `securities finance` | 56 | 23 | 0 |
| Management Development Programs | `repo` | 59 | 0 | 0 |
| Management Development Programs | `securities finance` | 1 | 1 | 0 |

L'union de la première catégorie contient 25 chemins, celle de la seconde un
chemin distinct. La référence contient 57 chemins Citi précédemment conservés.
La sonde ne relit que les détails inconnus : **aucun détail n'a donc été relu**.
Les scores, critères et dates actuels des offres connues n'ont pas été revérifiés.

Les totaux filtrés `repo` de 47 et 59 correspondent aux comptes annoncés dans la
page sans filtre. C'est un contrôle empirique cohérent de ces deux requêtes à cet
instant, pas une preuve générale que tous les filtres seraient honorés par Workday.
La sonde valide uniquement leur syntaxe et rapporte les valeurs envoyées.

La première sonde utilise 7 requêtes, la seconde 5, chacune incluant robots.txt.
Avec les deux requêtes de découverte réussie, cela représente **14 requêtes
abouties**, plus une tentative de transport échouée. Aucun retry interne ;
aucune limite de résultats, détails ou durée n'a été relevée.

## Portée des conclusions

- Une catégorie de métier ne garantit ni niveau junior, ni accès direct au trading.
- La catégorie de programmes n'est pas déclarée catalogue exhaustif des early careers.
- Le filtre de titres reste celui de la configuration ; les titres écartés ne sont
  pas évalués par leur description.
- Un chemin connu n'est pas une preuve que l'offre est inchangée, toujours ouverte
  ou accessible au candidat.
- Les autres catégories, termes et portails restent hors de cette mesure. Aucune
  fermeture ne peut être déduite de l'absence d'une offre dans un périmètre filtré.

Le gain de couverture observé est nul dans ces deux catégories avec ces deux termes.
Il ne justifie pas d'ajouter ces requêtes aux scans réguliers. Les filtres restent
disponibles pour de futures mesures ciblées à partir d'identifiants publics vérifiés.

Preuves immuables : `plan/`, `filtered-live/`, `programmes-live/` sous
`data/discovery/lot30/`, avec plan, rapport, détails et manifeste selon le mode.
Les tailles et SHA-256 de tous leurs manifestes ont été vérifiés. Les onze tables
de la base active sont identiques avant/après, preuve dans `preservation.json`.
