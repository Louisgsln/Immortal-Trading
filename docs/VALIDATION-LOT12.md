# Validation du lot 12 — Jump Trading et XTX Markets

17 septembre 2026, heure de Paris, Windows / Python 3.14.3. Les imports portent des timestamps UTC du 16 septembre à 22:11. Suite du [lot SIG et Flow Traders](VALIDATION-LOT11.md).

## Résultat

- **Jump Trading : 23 fiches importées** parmi 108 posts publics ; six scores ≥ 70 et onze scores ≥ 55.
- **XTX Markets : une fiche importée** parmi dix posts publics ; score 65.
- **Base et CSV : 746 fiches**, dont **145 scores ≥ 70** et **221 scores ≥ 55**.
- **21 sources activées pour 20 employeurs**. JPMorgan et Citadel Securities restent désactivés et n'ont pas été retestés pendant ce lot.

## Qualité des opportunités

[Campus Quantitative Trader (Full-Time), Londres/Amsterdam](https://www.jumptrading.com/hr/job?gh_jid=8050801) obtient **74/100**. Jump indique un contrat Full-time - Campus : le niveau junior est justifié, mais aucune année ni date de début ne l'est. Ce poste n'est donc pas présenté comme une promotion 2027. Les quatre Campus Quantitative Trader (Intern) restent conservés avec score nul.

[C++ Software Engineer chez XTX, Singapour](https://job-boards.greenhouse.io/xtxmarketstechnologies/jobs/7831489003) obtient **65/100**. Son titre seul ne précise pas le trading. Le département Tradingdev ETD Tech et les missions décrivant le développement des systèmes de trading permettent de retenir la fiche. Aucun statut junior ni début 2027 n'est inféré. Machine Learning Performance Engineer, du même département, décrit une autre fonction et ne bénéficie pas de cette classification.

Le score global mesure la proximité avec la cible ; il ne garantit pas l'éligibilité junior. Les exclusions de stage, séniorité et expérience minimale continuent de primer. Certains Quantitative Developer de Jump restent à score nul selon les règles techniques existantes, faute des preuves textuelles attendues ; la couverture des fonctions techniques reste prudente et incomplète.

## Imports et répétition

| Source et passage | Reçues | Nouvelles | Modifiées | Fermées | Alertes | Requêtes | Durée source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Jump — premier passage silencieux | 23 | 23 | 0 | 0 | 0 | 2 | 2,28 s |
| XTX — premier passage silencieux | 1 | 1 | 0 | 0 | 0 | 2 | 2,15 s |
| Jump — second passage | 23 | 0 | 0 | 0 | 0 | 2 | 2,27 s |
| XTX — second passage | 1 | 0 | 0 | 0 | 0 | 2 | 2,14 s |

Les seconds passages ne créent ni doublon ni modification artificielle. Le recalcul des 722 fiches précédentes ne change aucun score. Aucune notification envoyée et aucun watcher lancé.

Les autres employeurs n'ont pas été actualisés : les 746 fiches sont un historique conservé, pas une garantie de 746 postes encore ouverts. Les deux nouvelles collectes restent partielles (`complete=False`) et ne ferment aucune annonce sur sa seule absence.

## Preuves et contrôles des sources

Jump : les pages officielles [Students & New Grads](https://www.jumptrading.com/hr/students-new-grads) et [Experienced Candidates](https://www.jumptrading.com/hr/experienced-candidates) chargent explicitement l'API Greenhouse `jumptrading`. Le connecteur valide total, employeur, références, descriptions et URLs personnalisées `https://www.jumptrading.com/hr/job?gh_jid=ID`. Les paramètres supplémentaires, identifiants discordants et fragments sont refusés. Les trois valeurs de contrat publiées sont contrôlées. Jump Crypto, Jump Capital et inscriptions en vivier restent hors périmètre.

XTX : la [page officielle](https://www.xtxmarkets.com/careers/) relie le tableau `xtxmarketstechnologies` et charge un [miroir JSON public](https://api.xtxcareers.com/jobs.json). Les dix identifiants concordent avec l'API Greenhouse au moment de la découverte. Le connecteur utilise ensuite Greenhouse, sans dépendre d'un second appel au miroir à chaque scan. `metadata: null` est explicitement accepté chez XTX ; une clé absente reste une erreur. Le département et la rubrique The Role doivent corroborer une fonction technique de trading ; le texte générique de présentation de l'entreprise ne suffit pas.

Le champ facultatif `role_hint` est conservé dans le payload et dans l'historique des changements. Les anciens payloads restent compatibles. Aucune nouvelle dépendance ni migration de schéma SQLite n'est nécessaire.

## Vérifications

- **507 tests réussis**, dont **40 nouveaux** ; couverture globale **93 %**, Greenhouse filtré **99 %**.
- Ruff valide sur **70 fichiers** ; mypy valide sur **29 modules**.
- Tests de contrat, URL et identifiants Jump ; département, rubrique des missions et contre-exemples XTX ; exclusions prioritaires, rétrocompatibilité et historique du nouveau champ.
- SQLite et configuration valides via `doctor` ; alertes désactivées, Telegram non configuré, aucune alerte en base.
- Docker, CI distante et exploitation prolongée restent à valider.

## Suite logique

**Portails professionnels UBS et HSBC**, puis Nomura, en conservant leurs sources campus distinctes. Le [suivi de construction](ROADMAP.md) détaille les priorités restantes.

```powershell
.\.venv\Scripts\trading-radar.exe scan --source jump_trading
.\.venv\Scripts\trading-radar.exe scan --source xtx_markets
.\.venv\Scripts\trading-radar.exe doctor
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src
```
