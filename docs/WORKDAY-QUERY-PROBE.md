# Comparer des recherches publiques Workday

`scripts/probe_workday_queries.py` mesure le complément de deux recherches au maximum par rapport aux chemins déjà présents dans la base. Il ne modifie ni les sources configurées, ni les offres, ni les candidatures. Il ne déclenche aucune alerte et n'installe aucune surveillance.

## Préparer puis mesurer

Depuis la racine du projet, avec son environnement Python :

```powershell
.venv/Scripts/python.exe scripts/probe_workday_queries.py --output-dir data/discovery/lot27/citi-plan
.venv/Scripts/python.exe scripts/probe_workday_queries.py --network --source citi --term repo --term "securities finance" --output-dir data/discovery/lot27/citi-live
```

Sans `--network`, aucune connexion HTTP n'est ouverte. Les valeurs par défaut sont `citi`, `repo` et `securities finance`. Chaque invocation exige un **nouveau dossier** sous `data/discovery/lot27` ou `data/discovery/lot30`. Une mesure ne reprend pas le dossier du plan : elle relit la configuration et la référence locale au moment de son exécution.

## Restreindre une recherche par filtres publics

L'argument répétable `--facet KEY=VALUE` transmet un identifiant de filtre public Workday. Les clés et les valeurs doivent provenir du portail de carrière concerné : ne pas utiliser un libellé affiché à la place de son identifiant, ni inventer une valeur. Plusieurs occurrences d'une même clé regroupent ses valeurs dans `appliedFacets` ; Workday détermine la combinaison des filtres.

Exemple de syntaxe, avec des identifiants à remplacer par ceux effectivement observés sur le portail :

```powershell
.venv/Scripts/python.exe scripts/probe_workday_queries.py --source citi --term repo --facet "Country_and_Jurisdiction=IDENTIFIANT_PUBLIC_PAYS" --facet "jobFamilyGroup=IDENTIFIANT_PUBLIC_METIER" --output-dir data/discovery/lot30/citi-filtre-plan
```

Sans `--facet`, les filtres `applied_facets` de la configuration sont conservés, ou `{}` si aucun n'est configuré. Dès qu'un filtre est fourni, **l'ensemble des filtres configurés est remplacé** dans la copie en mémoire. Rien n'est écrit dans la configuration. Les appels Python à `build_plan(..., applied_facets={})` peuvent explicitement vider ce périmètre ; `None` conserve les filtres configurés.

Le plan et le rapport enregistrent exactement `applied_facets`. Un appel Python à `probe(config, plan)` utilise le périmètre enregistré même si la configuration a changé entre-temps. Pour compatibilité, un ancien plan sans ce champ reprend les filtres configurés. L'outil n'atteste pas que le portail a respecté un filtre : les résultats doivent encore être examinés.

Ces valeurs décrivent les filtres envoyés. Leur validation locale est syntaxique :
elle ne prouve pas l'existence de l'identifiant, son acceptation par le serveur,
ni la classification junior des postes. Une catégorie de métier ou de programmes
limite le périmètre étudié ; elle ne remplace pas la lecture des critères des offres.

Au maximum cinq clés sont acceptées : lettre ASCII initiale, puis lettres ASCII, chiffres ou `_`, sur 64 caractères maximum. Chaque clé reçoit de une à dix valeurs textuelles distinctes, non vides, de 128 caractères maximum, sans caractères de contrôle, de format ou de substitution Unicode. Les valeurs ne sont pas transformées. Un doublon exact, un argument sans `=`, ou un filtre invalide arrête la préparation avant toute connexion.

## Limites fixes

- Une source Workday activée ; un ou deux termes distincts, de 1 à 100 caractères.
- Au plus 200 résultats par recherche, pagination de 20 éléments.
- Au plus 12 chemins sélectionnés inconnus, dédupliqués entre recherches, puis 12 lectures de détail. Les chemins connus ne sont pas relus.
- Budget global de 180 secondes ; délai HTTP plafonné à 20 secondes ; aucun retry.
- Intervalle de la configuration, relevé à 2 secondes au minimum. `robots.txt` et ses délais éventuels restent applicables via `HTTPClient`.
- Les options de la configuration sont copiées en mémoire. Aucun argument ne permet d'augmenter ces limites.

Le dépassement d'une borne ou une réponse incohérente arrête la source, y compris les recherches suivantes. Un changement significatif de titre entre recherches ou entre liste et détail, ainsi qu'un identifiant de détail répété, rend la mesure incomplète. Une mesure incomplète sort avec le code `1`, conserve les observations déjà terminées et n'importe rien. Un refus de préparation sort aussi avec `1`, avec un message expurgé.

## Lire les résultats

- `plan.json` : termes, filtres `applied_facets`, limites et référence locale horodatée.
- `report.json` : filtres `applied_facets` utilisés, état `ok` ou `incomplete`, résultats bruts et sélectionnés par recherche, chemins connus et inconnus, score expliqué des détails intégralement lus, nombre de requêtes incluant `robots.txt`.
- `details.json` : liste de `RawJob` publics entièrement lus, utilisables pour une revue ultérieure ; ce fichier n'est jamais importé automatiquement.
- `manifest.json` : taille et SHA-256 des artefacts. `report.json` référence aussi le plan et les détails.

Le plan hors ligne ne produit que `plan.json` et `manifest.json`. Les écritures utilisent une création exclusive : aucun artefact n'est écrasé. Les dossiers existants et les ancêtres de type lien symbolique/jonction sont refusés. Un fichier existant, y compris un lien matériel vers la base ou un fichier synchronisé, ne peut pas être écrasé.

La référence lit `jobs` et `job_sources` dans une transaction SQLite `mode=ro`, `query_only=ON`, sans ouvrir le `Repository`. Elle couvre tous les chemins connus de cette source, y compris des observations anciennes. `latest_observation_at` est seulement le dernier horodatage individuel stocké : les écritures par offre ont des heures distinctes ; ce champ **ne reconstitue pas le dernier lot de scan**.

`unseen_paths` signifie « absent des chemins locaux connus », jamais « nouvelle publication sur le marché ». Le filtrage des titres reste celui de la source configurée. Les requêtes sont partielles : même `status: ok` ne garantit aucun inventaire exhaustif et ne permet pas d'inférer une fermeture. Les dates de mesure sont produites localement en UTC ; la publication éventuelle d'une offre reste un champ distinct du détail.

Les erreurs indiquent l'étape et un code sûr (`result_limit`, `detail_limit`, `time_limit`, `transport_error`, `robots_policy`, `duplicate_detail_id`, ou type générique). Aucun en-tête, cookie ou texte brut d'exception n'est enregistré. Une interruption du processus peut laisser un dossier sans manifeste final : il ne doit alors pas être considéré comme une mesure complète.

## Vérification locale

```powershell
.venv/Scripts/python.exe -m pytest tests/test_workday_query_probe.py
```

Les transports simulés couvrent le plan sans réseau, les filtres transmis et leur provenance dans les rapports, le remplacement ou l'héritage du périmètre configuré, les filtres malformés, les bornes, la pagination, les refus HTTP/robots, les titres divergents, les doublons d'identifiants, les détails partiels, les erreurs de référence, les artefacts immuables et la préservation de la base. Ils ne contactent pas Workday.
