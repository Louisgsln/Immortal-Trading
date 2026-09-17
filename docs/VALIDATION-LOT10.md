# Validation du lot 10 — IMC et DRW

16 septembre 2026, Windows / Python 3.14.3. Suite du [lot Optiver](VALIDATION-LOT9.md).

## Résultat

- **IMC : 26 fiches importées**, parmi 174 posts publics, dont 12 avec score ≥ 70 et 17 avec score ≥ 55.
- **DRW : 26 fiches importées**, parmi 153 posts publics du tableau anglais, dont 11 avec score ≥ 70.
- **Base et CSV : 663 fiches**, dont **131 avec score ≥ 70** et **197 avec score ≥ 55**.
- **Dix-sept sources activées pour seize employeurs**. Citadel Securities et JPMorgan restent désactivés ; leurs accès n'ont pas été retestés pendant ce lot.

## Postes juniors avec début 2027 explicite

| Employeur | Poste et lieu | Début publié | Score |
| --- | --- | --- | ---: |
| IMC | [Graduate Quantitative Trader — Chicago](https://job-boards.eu.greenhouse.io/imc/jobs/4751729101) | Février ou août 2027 | 84 |
| IMC | [Graduate Trader — Amsterdam](https://job-boards.eu.greenhouse.io/imc/jobs/4667815101) | Février ou août 2027 | 84 |
| DRW | [Quantitative Trading Analyst — Singapore](https://job-boards.greenhouse.io/drweng/jobs/8014946) | Summer 2027 | 96 |
| DRW | [Quantitative Trading Analyst — London](https://job-boards.greenhouse.io/drweng/jobs/7957241) | Summer 2027 | 96 |

Les deux fiches DRW demandent un diplôme obtenu entre décembre 2026 et juin 2027. IMC Chicago indique septembre 2026–juillet 2027 ; Amsterdam vise les étudiants en dernière année. Ces conditions restent dans les descriptions ; aucun matching au CV ni aucune validation d'éligibilité personnelle n'a été effectué.

DRW publie aussi une fiche Quantitative Trading Analyst à Londres avec une cible « Immediate », distincte du poste campus été 2027. Les références différentes sont conservées. Les autres scores élevés peuvent concerner des professionnels expérimentés ou des fonctions proches du trading : le seuil ne garantit pas un poste junior 2027.

## Imports et répétition

| Source et passage | Reçues | Nouvelles | Modifiées | Fermées | Alertes | Durée de source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| IMC — premier import silencieux | 26 | 26 | 0 | 0 | 0 | 4,3 s |
| DRW — premier import silencieux | 26 | 26 | 0 | 0 | 0 | 6,3 s |
| IMC — second import | 26 | 0 | 0 | 0 | 0 | 4,3 s |
| DRW — second import | 26 | 0 | 0 | 0 | 0 | 6,3 s |

Chaque passage combiné utilise quatre requêtes au total, dont la vérification robots, en environ 6,6 secondes. Le second ne crée ni doublon ni modification artificielle. Le recalcul préalable a enrichi les motifs d'exclusion de six anciennes fiches de recrutement, déjà à score nul ; les comptes des seuils existants sont restés identiques. Aucune notification n'a été envoyée et aucun watcher n'a été lancé.

## Fiabilité et classement

Les tableaux Greenhouse sont reliés aux fiches officielles, puis contrôlés par total, identifiant, employeur, domaine et référence de l'URL. Les descriptions doivent être présentes et non vides. Une incohérence fait échouer la collecte entière avant import. Les snapshots sont filtrés (`complete=False`) : aucune fermeture n'est déduite d'une absence. Le tableau IMC est global malgré le chemin `/us/` de sa page d'entrée.

Les prospect posts et les annonces IMC explicitement cachées sont ignorés. Les contrats de stage sont exclus même lorsqu'ils sont absents du titre. Quatre exclusions ciblées corrigent les faux positifs observés : recrutement, assistance administrative, étudiant salarié à temps partiel et spécialiste des applications de trading/fournisseurs. Les dates de début sont conservées sans choisir un mois parmi les alternatives ni inventer un jour précis. Publication et deadline ne proviennent que de champs explicites avec fuseau.

Les offres des autres sources n'ont pas été actualisées pendant ce lot. Les 663 fiches représentent l'historique conservé, avec stages et postes hors cible ; ce nombre ne garantit pas autant de postes ouverts.

## Vérifications

- **418 tests réussis**, dont 44 nouveaux ; **93 % de couverture globale**, **98 % du nouveau connecteur**.
- Ruff valide sur **64 fichiers** ; mypy valide sur **28 modules**.
- Tests de tableau incomplet, doublons, identités et URLs incohérentes, description absente, changement de métadonnées, visibilité, prospect posts, contrats, dates et plafonds de volume.
- `doctor` : SQLite et configuration valides ; alertes désactivées, Telegram non configuré, aucune alerte en base.
- Aucune nouvelle dépendance. Docker, CI distante et exploitation prolongée restent à valider.

## Suite logique

**SIG et Flow Traders**, puis Jump Trading et XTX Markets. Détails des sources et limites dans [SOURCES.md](SOURCES.md).

```powershell
.\.venv\Scripts\trading-radar.exe scan --source greenhouse_filtered
.\.venv\Scripts\trading-radar.exe list --min-score 70
.\.venv\Scripts\trading-radar.exe doctor
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src
```
