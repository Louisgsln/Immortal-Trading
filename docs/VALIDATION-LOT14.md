# Validation du lot 14 — Nomura professionnels

17 septembre 2026, heure de Paris, Windows / Python 3.14.3. Suite du [lot UBS et HSBC professionnels](VALIDATION-LOT13.md).

## Résultat

- **16 nouvelles fiches Nomura**, après lecture de 337 résultats Trading, filtrage des titres et exclusion de la division Operations.
- **Huit scores ≥ 70** et **neuf scores ≥ 55** pour cette source.
- **SQLite et CSV : 794 fiches**, dont **159 scores ≥ 70** et **243 scores ≥ 55**.
- **24 sources activées pour 20 employeurs**. Nomura campus reste une source distincte ; les autres employeurs n'ont pas été rescannés.

Ces nombres représentent l'historique conservé, pas une garantie de postes encore ouverts ou d'éligibilité junior. La recherche est partielle ; une absence ne ferme aucune fiche.

## Opportunités et corrections de classement

- [CLO Trading Analyst, New York](https://careers.nomura.com/Nomura/job/New-York-CLO-Trading-Analyst-NY-10019/1415971700/) : **84/100**, grade Analyst explicitement indiqué.
- [Credit Structurer – Analyst, Londres](https://careers.nomura.com/Nomura/job/London-Credit-Structurer-Analyst-Lond-EC4R-3AB/1422332900/) : **82/100**.
- [Temp Analyst (Structuring), Séoul](https://careers.nomura.com/Nomura/job/Seoul-Temp-Analyst-%28Structuring%29-100768/1391694200/) : **84/100**, contrat explicitement limité à douze mois. Aucun début 2027 ni programme graduate supposé.
- [Quantitative Structurer – Platform & AI, Londres](https://careers.nomura.com/Nomura/job/London-Quantitative-Structurer-Platform-&-AI-Lond-EC4R-3AB/1375202900/) : **score nul**, car le grade publié est Vice President / Executive Director malgré l'absence de séniorité dans le titre de l'annonce.

Lead Support Analyst – Low Latency Electronic Trading est une fonction de support informatique. Le titre reçoit désormais une exclusion explicite du classement prioritaire. En revanche, les deux Trading Support de Mumbai inspectés couvrent un rôle quant eFX et un rôle de financement de titres ; ils restent évalués avec leurs missions, grade et expérience publiés. Une exclusion générale du mot Support aurait masqué ces deux fiches.

Plusieurs références distinctes portent le titre GM-Global Markets. Elles restent séparées et leurs grades et minima d'expérience sont lus dans la description. Un titre générique ne suffit pas à garantir un poste de trader ; le score reste une aide au tri et les missions doivent être vérifiées avant candidature.

## Imports

| Passage | Reçues | Nouvelles | Modifiées | Fermées | Alertes | Requêtes | Durée source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Premier passage silencieux | 16 | 16 | 0 | 0 | 0 | 22 | 42,7 s |
| Second passage | 16 | 0 | 0 | 0 | 0 | 22 | 42,5 s |

Le second passage ne crée ni doublon ni modification artificielle. Le recalcul préalable des 778 fiches existantes ne change aucun score. Aucun watcher lancé, aucune notification envoyée. Les timestamps UTC des imports sont le 16 septembre à 22:48 et 22:49, soit le 17 septembre à Paris.

## Contrat de collecte

La [page régionale officielle des professionnels](https://www.nomura.com/asia/careers/experienced-professionals/) lie `careers.nomura.com/Nomura`. Son formulaire public GET lance une recherche par mot-clé. Les pages observées contiennent 100, 100, 100 puis 37 résultats. Le connecteur vérifie le mot demandé, les bornes et totaux annoncés, la présence des cartes, l'unicité des références et la stabilité de la première page relue à la fin. Cette vérification ne fournit pas de garantie transactionnelle côté serveur.

Les liens mobile et ordinateur d'une même carte doivent concorder. La division Operations est exclue avant lecture des détails : elle contient notamment Trading Controls Associate. Les titres eTrading sont explicitement inclus dans les options de cette source.

Chaque fiche conserve les missions et exigences intégrales. Le contrôle porte sur le titre, l'employeur, l'adresse, la référence de l'URL canonique, le lien de candidature et la publication UTC. Aucun formulaire de candidature n'est ouvert ou envoyé. Un détail manquant, une incohérence, une limite dépassée ou un catalogue mouvant fait échouer la source avant import partiel.

Les grades seniors et les minima d'expérience alimentent les champs déjà existants du modèle. Les références au management dans le texte générique ne déclenchent pas d'indice de séniorité : il faut le libellé Corporate Title. Le minimum d'expérience provient d'une rubrique Experience explicite ; les exigences plus fortes du moteur de score continuent de primer.

`datePosted` au format UTC est conservé comme publication. `validThrough` reste une preuve dans le payload brut optionnel et n'est pas transformé en deadline candidat. Aucune date de début n'est déduite. Aucun changement de schéma SQLite ou de dépendance.

## Limites

- Recherche Trading et filtre de titres ciblé : des postes de stratégie quantitative ou de structuration sans les termes attendus peuvent être manqués.
- Laser Digital et les portails japonais distincts sont hors périmètre.
- Nomura campus n'a pas été actualisé pendant ce lot. JPMorgan et Citadel Securities restent désactivés et n'ont pas été retestés.
- Pas de clôture par absence dans cet inventaire partiel ; pas de promesse de fraîcheur pour les autres sources.

## Vérifications

- **631 tests réussis**, dont **51 nouveaux** ; couverture globale **94 %**, Nomura professionnels **96 %**.
- Ruff valide sur **79 fichiers** ; mypy valide sur **31 modules**.
- `doctor` : configuration et SQLite valides, alertes désactivées, Telegram non configuré. Aucune alerte en base ; CSV et SQLite concordent sur 794 fiches.
- Tests de pagination, doublons d'affichage et de référence, catalogue instable, limites, réponse vide explicite, conservation de la recherche, URLs, identité des détails, grades, expérience et contrat à durée déterminée.
- Exclusions seniors vérifiées malgré un titre Analyst ; contre-exemple Trading Support conservé pour éviter une exclusion trop large.
- Docker, CI distante et surveillance prolongée restent à valider.

## Suite logique

**Audit de couverture et de fraîcheur des sources existantes**, en commençant par les recherches Workday limitées à Trading, puis suivi des candidatures. Priorités dans [ROADMAP.md](ROADMAP.md), contrat détaillé dans [SOURCES.md](SOURCES.md).

```powershell
.\.venv\Scripts\trading-radar.exe scan --source nomura_professionals
.\.venv\Scripts\trading-radar.exe doctor
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src
```
