# Lot 23 — mesure réelle du cache Workday

## Résultat du 17 septembre 2026

Une fiche active existante par source a été relue deux fois le 17 septembre à
00:55 UTC. Les huit lectures de détail ont répondu `200`, sans `ETag` ni
`Last-Modified`. Toutes comportaient `Cache-Control: no-store, no-cache`,
`Vary: accept-encoding` et `Set-Cookie`.

**Aucune réponse n'a été conservée ou réutilisée par le cache. Aucun gain de cache
n'est établi sur cet échantillon.** L'option `conditional_details` reste désactivée
dans la configuration de production. Les règles du serveur ne sont pas contournées.

| Source | Réponses détail | Corps décodé, lecture 1 / 2 | Corps téléchargé, lecture 1 / 2 | Réutilisation |
| --- | --- | ---: | ---: | --- |
| Barclays | 200 / 200 | 9 587 / 9 587 octets | 4 554 / 4 473 octets | Non |
| Deutsche Bank | 200 / 200 | 5 603 / 5 603 octets | 2 856 / 2 856 octets | Non |
| Morgan Stanley | 200 / 200 | 8 552 / 8 552 octets | 4 006 / 4 006 octets | Non |
| Citi | 200 / 200 | 8 105 / 8 105 octets | 3 318 / 3 357 octets | Non |

`decoded_body_bytes` mesure le corps après décompression.
`downloaded_body_bytes` vient du compteur HTTPX `num_bytes_downloaded` et mesure
les octets du corps reçus, avant décompression ; les en-têtes HTTP et le transport
TLS ne sont pas inclus. Les petites variations entre deux `200` ne constituent
pas une économie attribuable au cache.

La sonde a effectué **12 requêtes** : quatre lectures de robots et huit détails.
Les quatre fiches décodées sont identiques entre leurs deux lectures. Cette mesure
porte sur quatre fiches à un instant donné ; elle ne garantit pas le comportement
des autres fiches ni des réponses futures. Elle ne constitue pas une collecte
complète ni une actualisation des offres en base.

## Reproduction

Depuis la racine du projet, afficher et enregistrer le plan sans accès réseau :

```powershell
.venv/Scripts/python.exe scripts/measure_workday_cache.py
```

Activer explicitement la sonde bornée :

```powershell
.venv/Scripts/python.exe scripts/measure_workday_cache.py --network --output data/discovery/lot23/workday-cache/live-report.json
```

Le script choisit l'offre active de meilleur score par source Workday activée,
puis départage par identifiant. Il refuse plus de quatre sources. Une source sans
offre active est ignorée. Les URL doivent appartenir au site Workday configuré,
et leurs chemins sont validés par l'adaptateur existant.

La sélection utilise SQLite `mode=ro`, `query_only` et une transaction de lecture.
Le script ne crée pas de `Repository`, n'écrit pas dans la base, ne lance ni
recherche POST ni notification et ne modifie pas la configuration. Seul son
rapport JSON est écrit sous `data/discovery`. Relancer avec le même chemin remplace
ce rapport.
La base et ses fichiers annexes sont protégés contre l'écrasement, y compris
leurs alias par lien physique. En mode réseau, le code de sortie vaut `1` si au
moins une source est indisponible ; le rapport reste enregistré pour diagnostic.
Un résultat sans réutilisation de cache mais avec deux lectures réussies est un
succès de mesure et conserve le code `0`.

Le client HTTP du projet applique robots, la cadence configurée et `Crawl-delay`.
Chaque source est limitée à 90 secondes, avec un délai réseau maximal de 20
secondes par requête et zéro retry. Un refus, une redirection, une réponse
incomplète ou une erreur interrompt les lectures de cette source.

Les deux lectures utilisent le même client et un cache partagé en mémoire. La
production recrée normalement le client entre scans ; ce test court mesure
l'éligibilité des réponses au cache et leur revalidation, pas les performances
d'un watcher complet. Aucun contenu de fiche, cookie ou jeton n'est enregistré :
les cookies ne sont représentés que par leur présence booléenne. Seuls les
validateurs et les métadonnées HTTP nécessaires figurent dans le rapport.

## Preuves et vérification

- Résultat réseau : `data/discovery/lot23/workday-cache/live-report.json`.
- Premier essai en sandbox : `data/discovery/lot23/workday-cache/report.json` ;
  quatre erreurs de transport, aucune réponse HTTP. Il ne mesure pas les serveurs.
- Tests : `tests/test_workday_measurement.py` (transport HTTP simulé).
- Garanties du cache : [WORKDAY-CACHE.md](WORKDAY-CACHE.md).

Les tests vérifient l'absence de réseau sans `--network`, la sélection bornée en
lecture seule, les chemins publics, le cycle `200`/`304`, les réponses non
stockables, l'arrêt aux refus sans retry, la non-divulgation des cookies, les
sources sans offre et le refus d'un plan dépassant quatre sources.
