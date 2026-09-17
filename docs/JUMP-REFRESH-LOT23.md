# Actualisation Jump — lot 23

## Collecte publique et rejeu

`scripts/refresh_jump_lot23.py` capture un catalogue Greenhouse public de Jump via le client HTTP du projet : contrôle robots, cadence configurée, HTTPS, aucun suivi des redirections et aucun nouvel essai automatique. L'accès réseau exige l'option explicite `--network`.

```powershell
.venv/Scripts/python.exe scripts/refresh_jump_lot23.py --network
```

Les preuves sont conservées dans `data/discovery/lot23/jump/` :

- `catalogue.json` : octets de la réponse publique, sans réécriture JSON ;
- `capture.json` : URL, source, horodatages UTC, nombre d'octets, SHA256 et statuts HTTP ;
- `analysis.json` : inventaire comparé au lot 12 et aux identités Jump de la base ;
- `collection.json` : offres brutes retenues par le parseur courant, `complete=false` et `requests=0` pour un rejeu local.

Les cookies et les en-têtes HTTP ne sont pas archivés. Un catalogue déjà présent n'est pas écrasé. Un échec d'accès produit `capture-failure.json` et interrompt la collecte.

Les sorties doivent rester dans un sous-dossier dédié de `data/discovery`, après résolution des chemins. Les alias vers la base SQLite et ses fichiers auxiliaires sont refusés, y compris les liens physiques. `sources/` ne constitue jamais une destination valide.

Recalculer l'analyse avec le code courant, sans accès réseau :

```powershell
.venv/Scripts/python.exe scripts/refresh_jump_lot23.py
```

`load_capture(path)` renvoie `(payload, manifest)` après validation de la source, de l'URL exacte, du SHA256, de la taille et de l'horodatage avec fuseau. Le parseur vérifie ensuite le contrat Greenhouse : total exact, identifiants uniques, employeur, URL officielle de chaque offre, métadonnées et descriptions attendues. Le manifeste assure la cohérence locale de l'archive ; ce n'est pas une signature cryptographique du fournisseur.

## Périmètre et préservation

Le script ouvre SQLite en `mode=ro`, active `query_only` et lit les identités Jump dans une transaction. Il n'initialise ni `Repository`, ni scanner, ni notificateur. Il ne modifie aucune offre ou candidature. Les comptes de scores représentent les offres sélectionnées par le code courant, pas l'intégralité du catalogue public.

Le collecteur reste partiel : des métiers et contrats hors périmètre sont exclus. Une offre absente de la sélection ou du catalogue comparé ne permet aucune fermeture automatique (`complete=false`, `absence_can_close=false`).

L'importation est une étape distincte, précédée d'une répétition sur copie SQLite et d'une sauvegarde. Elle réutilise l'archive validée sans refaire de requête au site.

## Résultats

Le 17 septembre 2026 à 00:56:12 UTC, le serveur a retourné 108 lignes et 1 028 767 octets. Les deux requêtes réussies sont `robots.txt` (200), puis le catalogue (200), espacées d'environ deux secondes. Le SHA256 du catalogue est `7ae8cfe810a1398e3289e800e55dc54b5209fd959d477a044ee2d64df515fb49` : la réponse est identique octet pour octet au corpus du lot 12. L'évolution attendue des offres retenues vient donc du parseur et de la reconnaissance d'expérience.

Une tentative initiale dans le bac à sable a échoué au niveau transport avant toute réponse ; `capture-failure.json` en conserve la trace. La collecte ci-dessus a réussi après autorisation d'accès réseau, avec les mêmes contrôles du client.

L'analyse précédant l'import a retenu 25 offres, contre 23 identités Jump déjà stockées ; les deux nouvelles identités sont `7822791` et `8104832`. Aucune identité précédemment stockée n'a disparu de la sélection. Six offres retenues atteignent 70 points et onze atteignent 55 points. `analysis.json` conserve cet état avant import ; un rejeu ultérieur observe naturellement la base actualisée.

Après répétition sur copie, l'import distinct a reçu 25 offres, ajouté deux offres et actualisé quatre offres, sans fermeture ni alerte. Les preuves sont `data/discovery/lot23/rehearsal.json` et `data/discovery/lot23/import.json`. Les deux étapes réutilisent la même archive validée sans accès supplémentaire au catalogue.

Les vingt tests de `tests/test_jump_refresh.py` vérifient notamment la provenance et les altérations de l'archive, le refus d'un total incohérent, le rejeu sans initialisation HTTP ni modification SQLite, les destinations hors périmètre et les liens physiques vers la base ou ses fichiers auxiliaires. Ruff et mypy passent sur le script.
