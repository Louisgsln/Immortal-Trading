# Intégrité des détails Workday — lot 27

## Problème et changement

Le collecteur sélectionnait un titre dans la recherche, puis importait le détail sans
vérifier que son titre correspondait encore. Des champs JSON mal typés pouvaient
être convertis en identifiant texte (`str(dict)`), ignorés dans les lieux, ou produire
une erreur Pydantic plutôt qu'une erreur de source. Deux chemins distincts portant
le même identifiant stable pouvaient aussi arriver dans une collection réussie ;
leur import aurait alors dépendu de l'ordre des réponses.

Le collecteur refuse désormais la collection entière avec `SourceUnavailable` si :

- le titre ou la description manque, est vide après retrait des espaces, ou n'est
  pas une chaîne ;
- un champ consommé présent est mal typé : `id`, `jobReqId`, `location`,
  `locationsText`, `startDate`, `timeType`, `additionalLocations` ou son descripteur ;
- le titre du détail diffère de celui de la recherche, après normalisation limitée ;
- un identifiant stable apparaît dans les détails de plusieurs chemins distincts.

Les messages n'incorporent pas les valeurs reçues. Les offres déjà lues ne sont pas
retournées sous forme de collection partielle réussie. Une recherche Workday reste
toujours `complete=False` : l'absence d'une offre ne permet pas de la fermer.

## Compatibilité conservée

La comparaison des titres applique `html.unescape`, Unicode NFKC, `casefold` et la
réduction des espaces. La ponctuation et les caractères non latins restent présents :
« Trading Analyst 東京 » ne devient pas identique à « Trading Analyst 北京 ».
Cette même comparaison s'applique à un chemin répété entre deux requêtes de recherche.
Le titre original du détail reste enregistré sans réécriture.

Les champs optionnels absents ou `null` restent acceptés. Les lieux supplémentaires
acceptent une chaîne ou un objet avec un `descriptor` textuel. Le lieu de la recherche
sert toujours de repli. Une date textuelle non reconnue reste inconnue.

Un `id` textuel non vide est préféré ; sinon `jobReqId` sert de repli. Aucun lien
arbitraire n'est exigé entre l'identifiant stable, le numéro de réquisition et le
suffixe du chemin. Deux identifiants stables distincts peuvent partager un `jobReqId`.
Le même chemin retrouvé par plusieurs requêtes ne déclenche qu'une lecture de détail.

Deux chemins distincts avec le même identifiant sont refusés même si leurs contenus
sont identiques : les archives examinées ne démontrent aucun contrat d'alias qui
permettrait de choisir une URL canonique en sécurité. Une future prise en charge
d'alias devra s'appuyer sur des exemples vérifiés.

La mesure du cache peut appeler `_detail(path, {})` sans recherche préalable : elle
valide les champs du détail mais ne peut comparer le titre avec un listing absent.
Les collectes normales fournissent toujours le titre validé par `_search`. Le cache
conditionnel reste une option désactivée par défaut.

## Vérification hors réseau — 17 septembre 2026

Les 16 couples recherche/détail archivés dans le lot 15 ont été rejoués par le
collecteur avec `httpx.MockTransport`. Le résultat de chaque `_detail` est exactement
égal à `RawJob.model_validate(archive).model_dump()`, y compris URLs, dates, contenu
et `raw_payload`. Aucun accès réseau ni modification de base n'a été effectué.

| Archive sous `data/discovery/lot15/` | Offres | Titres identiques avant normalisation |
| --- | ---: | ---: |
| `barclays-extra-jobs.json` | 6 | 6 |
| `deutsche_bank-extra-jobs.json` | 7 | 7 |
| `morgan_stanley-extra-jobs.json` | 3 | 3 |

Empreintes SHA-256 des fichiers d'entrée :

```text
barclays        114f7b976c1b7846ddd728e9ced309ca570e374b62d0b850c42fd999872996c7
deutsche_bank   4d53235923d454e3892299e61e454b9afc4f168ec8bd1013988237c43d9c81af
morgan_stanley  bc304187873f428b297401a85d5a9e5234bfef40106ceabfe678a1003a8c76e7
```

Empreintes des listes de `RawJob.model_dump(mode="json")` dans l'ordre des archives,
sérialisées en UTF-8 avec `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)` :

```text
barclays        54c6415645f40bb7c5ed015cf19f8d43455cde70a2e9eaa682ce40649bd8177d
deutsche_bank   b6dc8c87c85857e27c06f342a910453388dbd287086d8d0deecf76da3a134832
morgan_stanley  7ca5c19bedbbe86c5fb63f3ffe3f909389ffb2ba57806c30c852286281c2f2ea
```

Les fixtures ajoutent les cas qui ne figurent pas dans ces archives : valeurs
mal typées, champs absents, alias de présentation, titres réellement différents,
identifiants répétés entre chemins et réquisitions partagées.

Validation ciblée : **102 tests réussis**, dont **52 nouveaux tests d'intégrité**,
avec les tests existants du collecteur, du cache et du script de mesure.
Ruff et mypy passent sur le code concerné.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_workday_integrity.py tests/test_workday.py tests/test_workday_cache.py tests/test_workday_measurement.py
```

Cette vérification décrit le corpus archivé et les contrats testés. Elle ne prouve
pas l'exhaustivité actuelle des recherches ni la disponibilité des sites distants.

Une lecture SQLite avec `mode=ro` de `data/jobs.db` a également recensé 125 offres
Workday : Citi 57, Deutsche Bank 25, Barclays 22 et Morgan Stanley 21. Aucune ne
conserve un `raw_payload` comprenant le couple `listing` / `detail` ; elles ne
peuvent donc pas être rejouées depuis cette base. En particulier, la compatibilité
du détail Citi n'est pas démontrée par le corpus de 16 archives ci-dessus.
