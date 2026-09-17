# Validation du lot 11 — SIG / Susquehanna et Flow Traders

16 septembre 2026, Windows / Python 3.14.3. Suite du [lot IMC et DRW](VALIDATION-LOT10.md).

## Résultat

- **SIG : 49 fiches importées**, après lecture de 265 références publiques, filtre de titres et exclusion des catégories hors cible. Deux fiches avec score ≥ 70, six avec score ≥ 55.
- **Flow Traders : 10 fiches importées**, parmi 41 posts publics. Six fiches avec score ≥ 70.
- **Base et CSV : 722 fiches**, dont **139 avec score ≥ 70** et **209 avec score ≥ 55**.
- **Dix-neuf sources activées pour dix-huit employeurs**. Citadel Securities et JPMorgan restent désactivés et n'ont pas été retestés pendant ce lot.

## Qualité des opportunités

Le poste [Graduate Quantitative Trader — New York](https://job-boards.greenhouse.io/flowtraders/jobs/8094581) obtient **86/100**. Le texte annonce « Fall 2027 » ; la métadonnée Start Date indique **2027-08-30**. Ces formulations sont conservées comme preuves publiées, sans promettre une date de début confirmée pour le candidat. Flow Traders propose aussi Graduate Trader à Amsterdam (82) et Hong Kong (76) : Amsterdam conserve une métadonnée ancienne, 2026-06-01, et accepte les candidatures toute l'année ; Hong Kong n'indique pas de début. Aucune promotion 2027 n'est déduite pour ces deux fiches.

SIG présente une incohérence importante : **dix fiches classées New Graduates portent aussi un contrat INTERN**, dont Quantitative Trader — Graduate 2027 à Londres et Dublin. Les deux indications sont conservées ; le contrat stage entraîne un score nul. Ce choix évite une priorité trompeuse, mais peut écarter de véritables postes diplômés : une vérification auprès de la source reste nécessaire pour résoudre ces contradictions. Le contrat n'a pas été corrigé à partir d'une supposition.

Les deux scores SIG ≥ 70 concernent C# Developer — Core Trading Technology et Derivatives Sales Trader | Experienced Hire. Ils ne sont pas présentés comme programmes graduate 2027. Les trois Digital Assets Trader de Flow Traders dépassent aussi 70 tout en demandant plus de deux ans d'expérience ; leur score junior est nul. Le score global demeure un classement de proximité, pas une garantie d'éligibilité junior.

## Imports et répétition

| Source et passage | Reçues | Nouvelles | Modifiées | Fermées | Alertes | Requêtes | Durée source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SIG — premier passage silencieux | 49 | 49 | 0 | 0 | 0 | 5 | 18,2 s |
| Flow Traders — premier passage silencieux | 10 | 10 | 0 | 0 | 0 | 2 | 2,2 s |
| SIG — second passage | 49 | 0 | 0 | 0 | 0 | 5 | 18,7 s |
| Flow Traders — second passage | 10 | 0 | 0 | 0 | 0 | 2 | 2,4 s |

Les seconds imports ne créent ni doublon ni modification artificielle. Aucun watcher n'a été démarré, aucune notification envoyée. Les autres employeurs n'ont pas été actualisés : les 722 fiches représentent l'historique conservé, y compris les stages et postes hors cible, et ne garantissent pas autant de postes encore ouverts.

## Contrôles de collecte

SIG : catalogue public iCIMS/Jibe avec trois pages de 100, 100 et 65 offres. Totaux, identités, employeur, langue et visibilité sont contrôlés. La première page est relue pour détecter un changement du catalogue ; le serveur ne fournit pas de garantie transactionnelle entre pages. Les descriptions incluent les exigences candidat, sans les doubler lorsqu'elles sont déjà intégrées. Les URLs de connexion candidat ne sont jamais suivies ; les liens conservés ouvrent les fiches publiques.

Les programmes Discovery, fonctions Operations et Sports Analytics sont exclus du périmètre SIG. Les deux Trading Desk Associate vérifiés sont des fonctions opérationnelles, malgré leurs titres proches du trading. La catégorie Interns + Co-ops et les contrats INTERN excluent les stages de la priorité. La publication et le mois cible viennent des champs explicites ; aucune deadline n'est déduite du `validThrough` technique.

Flow Traders : extension du connecteur Greenhouse existant, sans nouvelle dépendance. Division Events exclut les événements et le vivier identifiés. Les dates Start Date doivent être des dates ISO valides ; une valeur vide reste inconnue et une date ancienne ne ferme pas l'annonce. Les deux sources restent filtrées (`complete=False`) : aucune fermeture n'est inférée de l'absence. Une collecte invalide échoue avant tout import partiel.

## Vérifications

- **467 tests réussis**, dont **49 nouveaux** ; couverture globale **93 %**, SIG **98 %**, Greenhouse filtré **99 %**.
- Ruff valide sur **68 fichiers** ; mypy valide sur **29 modules**.
- Tests de pagination, changements de total/page, doublons, schéma, visibilité, descriptions, catégories, conflits de contrat, dates et limites de volume.
- `doctor` : configuration et SQLite valides, alertes désactivées, Telegram non configuré ; aucune alerte en base.
- Aucune modification du moteur de score global ni de dépendance. Docker, CI distante et exploitation prolongée restent à valider.

## Suite logique

**Jump Trading et XTX Markets**, puis amélioration de la couverture bancaire et du suivi de candidature. Les contrats et limites des sources sont décrits dans [SOURCES.md](SOURCES.md).

```powershell
.\.venv\Scripts\trading-radar.exe scan --source sig
.\.venv\Scripts\trading-radar.exe scan --source flow_traders
.\.venv\Scripts\trading-radar.exe doctor
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src
```
