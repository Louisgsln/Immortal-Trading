# Validation du lot 9 — Optiver et vérification Citadel Securities

16 septembre 2026, Windows / Python 3.14.3. Suite du [lot Macquarie et Nomura](VALIDATION-LOT8.md).

## Résultat

- **Optiver : 27 fiches importées**, après parcours de 165 cartes publiques et filtre des titres.
- **Base et CSV : 611 fiches enregistrées**, dont **108 avec un score ≥ 70** et **169 avec un score ≥ 55**.
- **Quinze sources activées pour quatorze employeurs**. Goldman Sachs conserve ses deux sources professionnelle et campus.
- **Citadel Securities désactivé** : HTTP 403 lors de la lecture du portail par le client du projet. Aucun connecteur implémenté ni import présenté comme validé pour cet employeur.

Les autres employeurs n'ont pas été actualisés pendant ce lot. Ces nombres représentent les fiches conservées, y compris les stages et les annonces non confirmées comme encore ouvertes ; ils ne constituent pas un inventaire garanti de postes junior disponibles.

## Imports et répétition

| Passage Optiver | Reçues | Nouvelles | Modifiées | Fermées | Alertes | Requêtes | Durée |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Premier import silencieux | 27 | 27 | 0 | 0 | 0 | 40 | 79 s |
| Second import | 27 | 0 | 0 | 0 | 0 | 40 | 79 s |

Le second passage ne crée ni doublon ni modification artificielle. Le CSV contient 611 lignes d'offres. Aucun watcher n'a été démarré.

## Qualité du classement

Les cinq fiches Optiver avec score ≥ 70 sont : European Bonds Trader / German Bunds Trader, Options Trader (Taipei), Institutional Trader (Chicago), Positional Options Trader (Sydney), Digital Assets Trader (Crypto Options, Singapore). Elles sont classées Experienced par l'employeur. **Aucune n'est confirmée comme programme graduate 2027**. Leur contribution junior reste de 5/20 : le seuil total mesure aussi la proximité métier, les actifs et les compétences, et ne garantit pas l'éligibilité junior.

Graduate et Early Careers alimentent l'indice junior. Internship est conservé comme type de contrat ; les stages sont exclus même sans mention dans le titre. Experienced n'est pas assimilé arbitrairement à Senior ou à un nombre d'années précis.

Deux faux positifs ont été corrigés après lecture du contenu : Career Kickstarter est un programme de découverte de cinq jours avec possibilité d'offre ultérieure ; Expressions of Interest annonce la fermeture des candidatures formelles et une inscription au vivier. Les deux fiches restent consultables mais leur score vaut zéro, grâce à des exclusions de titres explicites. The Trading Floor est un événement et reste hors du filtre de collecte. Le recalcul hors réseau n'a changé aucun score déjà importé avec ces règles.

## Contrat de collecte

L'API publique `/en/api/v1/jobs?from=0&size=16` est celle du site officiel, vérifiée dans son client web et sur une deuxième page réelle. Onze pages couvrent le catalogue observé ; une nouvelle lecture de la première page détecte un changement de total ou d'ordre avant les détails. Totaux, tailles, doublons de cartes et URLs hors du domaine attendu font échouer la collecte. La vérification ne rend pas le catalogue distant transactionnel : une modification intermédiaire conservant le même début et le même total peut échapper au contrôle.

Les fiches sont contrôlées par titre, URL canonique, identité JobPosting, lieu, département et niveau. L'identifiant de l'offre vient de `meta jobid`. Seule la section de description est extraite ; les recommandations et pieds de page sont exclus. Dates de publication sans heure/fuseau, début d'emploi et deadline non structurés restent inconnus dans les champs normalisés, avec le contexte des dates conservé dans la description lorsqu'il existe.

Le snapshot reste `complete=False` car les titres sont filtrés : aucune fermeture n'est déduite d'une absence. La collecte échoue intégralement si une fiche échoue ; l'import d'une source reste atomique. Les plafonds de volume et de durée, robots et espacement de deux secondes sont conservés. Aucun formulaire n'est soumis.

## Vérifications locales

- **374 tests réussis**, dont 41 nouveaux tests Optiver ; **93 % de couverture globale**, 97 % pour le connecteur.
- Ruff : analyse et formatage valides sur **60 fichiers** ; mypy : **27 modules** sans erreur.
- Tests de pagination, répétition/changement de pages, schéma incomplet, domaine des liens, identité des fiches, budgets, erreurs de détails et doublons d'identifiants.
- Tests de classement des stages, événements et viviers ; source filtrée toujours incomplète pour la logique de fermeture.
- `doctor` : configuration et SQLite valides ; alertes désactivées, Telegram non configuré, aucune alerte en base.
- Aucune nouvelle dépendance. Docker et CI hébergée restent non exécutés dans cet environnement.

## Suite logique

Connecter **IMC et DRW**, puis SIG, Flow Traders, Jump Trading et XTX Markets. Citadel Securities reste en attente d'un accès public exploitable. Les portails professionnels UBS, HSBC et Nomura restent des périmètres distincts à ajouter.

```powershell
.\.venv\Scripts\trading-radar.exe scan --source optiver
.\.venv\Scripts\trading-radar.exe stats
.\.venv\Scripts\trading-radar.exe doctor
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src
```
