# Validation du lot 13 — UBS et HSBC professionnels

17 septembre 2026, heure de Paris, Windows / Python 3.14.3. Suite du [lot Jump et XTX](VALIDATION-LOT12.md).

## Résultat

- **UBS professionnels : 30 nouvelles fiches**, après lecture des 547 annonces du tableau public ; six scores ≥ 70 et douze scores ≥ 55.
- **HSBC professionnels : deux nouvelles fiches**, après pagination des 118 résultats de la recherche Trading, filtrage des titres et exclusion de la division Wealth & Premier Banking. Un score ≥ 55, aucun ≥ 70.
- **SQLite et CSV : 778 fiches**, dont **151 scores ≥ 70** et **234 scores ≥ 55**.
- **23 sources activées pour 20 employeurs**. Les sources campus UBS et HSBC restent distinctes ; les autres employeurs n'ont pas été rescannés pendant ce lot.

Ces comptes représentent les fiches conservées, y compris celles hors priorité. Ils ne garantissent pas autant de postes encore ouverts. Les collectes sont partielles et ne ferment pas une offre sur sa seule absence.

## Qualité des opportunités

[Electronic Trading Quantitative Analyst, New York](https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?PageType=JobDetails&jobid=342483&partnerid=25008&siteid=5012) obtient **92/100**. Les missions concernent les algorithmes d'exécution et l'analyse de données ; le texte exprime une préférence pour deux ans ou plus d'expérience. Ce n'est pas un programme graduate 2027 et aucune date de début n'est déduite.

Deux faux positifs UBS ont été corrigés : Global Markets Legal et Global Markets APAC COO - Business Manager. Les exclusions de titre Legal, COO et Business Manager empêchent de les prioriser à partir des mots Markets/Trading. Le recalcul des anciennes données actualise aussi les explications de deux annonces juridiques Jane Street, déjà à score nul ; leurs scores restent nuls.

Chez HSBC, [Fixed Income Trading Associate, Istanbul](https://portal.careers.hsbc.com/careers/job/563774612243958) obtient **68/100**, avec quatre années minimales demandées et une composante junior nulle. L'autre fiche, Corporate Sales à Séoul, reste à score nul par l'exclusion de vente pure. Le score global ne garantit pas l'éligibilité junior.

La prévisualisation HSBC trouvait aussi trois fiches de Wealth & Premier Banking, dont Product Specialist / Trader et Securities and Trading Product Manager. Les missions concernent le conseil patrimonial, la distribution ou l'offre de trading destinée aux particuliers ; ces fiches sont exclues du périmètre avant import. Le département publié sert de preuve, sans généraliser l'exclusion à partir d'un paragraphe générique sur la banque.

## Imports

| Source et passage | Reçues | Nouvelles | Modifiées | Fermées | Alertes | Requêtes | Durée source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| UBS — premier passage silencieux | 30 | 30 | 0 | 0 | 0 | 43 | 88,1 s |
| HSBC — premier passage silencieux | 2 | 2 | 0 | 0 | 0 | 16 | 30,6 s |
| UBS — second passage | 30 | 0 | 0 | 0 | 0 | 43 | 85,1 s |
| HSBC — second passage | 2 | 0 | 0 | 0 | 0 | 16 | 30,5 s |

Les seconds passages ne créent ni doublon ni modification artificielle. Aucun watcher lancé et aucune notification envoyée. Les imports ont eu lieu le 17 septembre à Paris, avec des timestamps UTC du 16 septembre entre 22:30 et 22:36.

## Sources et dates

UBS : le site officiel distingue les tableaux professionnels (`siteid=5012`, `LinkID=15231`) et campus. Le collecteur valide le bootstrap anonyme de la source choisie puis pagine tout le tableau, avant sélection Trading/Markets. Les missions et exigences sont conservées. Aucune donnée de session n'entre dans les offres stockées.

HSBC : lecture GET de la recherche Eightfold publique par pages de dix, contrôle du total et des doublons, puis relecture de la première page. Chaque fiche doit confirmer la position, le titre, les lieux, l'employeur et une description JobPosting complète. Une fiche privée, une redirection ou un catalogue incohérent fait échouer la source avant import partiel. Les fonctions candidat ne sont pas appelées.

Les horodatages techniques de la plateforme et les dates sans fuseau ne deviennent pas de fausses dates de publication ou deadlines. La présence de `validThrough` ne prouve pas une échéance de candidature. Aucune date 2027 ni séniorité n'est inférée du seul portail professionnel.

La couverture HSBC reste limitée à la recherche Trading et aux titres ciblés. Des postes Dealer ou techniques sans les termes attendus peuvent être manqués. Les nouveaux filtres métier et la politique des dates sont détaillés dans [SOURCES.md](SOURCES.md).

## Contrôle robots corrigé

Le lecteur standard Python retenait l'interdiction générale de HSBC avant ses autorisations plus précises. **Protego 0.6.2** a été ajouté pour appliquer correctement Allow/Disallow, les jokers, les groupes d'agent et Crawl-delay. Le délai découvert s'applique dès la première page suivant robots.txt. Les chemins interdits restent bloqués ; les refus 401/403 et les politiques indisponibles conservent leur comportement d'échec fermé. Il s'agit d'une correction de lecture des règles publiées, pas d'une exception propre à HSBC.

## Vérifications

- **580 tests réussis**, dont **73 nouveaux** ; couverture globale **94 %**, HSBC professionnels **96 %**, UBS **93 %**.
- Ruff valide sur **75 fichiers** ; mypy valide sur **30 modules** ; `pip check` sans conflit.
- `doctor` : configuration et SQLite valides, alertes désactivées, Telegram non configuré. Aucune alerte en base ; CSV et base contiennent chacun 778 fiches après le dernier import.
- Tests des contextes UBS campus/professionnels, pagination, total instable, pages répétées, titres/identités discordants, données manquantes, annonces privées, exclusion Wealth, déduplication entre requêtes et absence de données candidat dans les offres.
- Tests robots avec chemins autorisés et interdits, priorité des règles, jokers, encodage, groupes d'agent, cache et espacement effectif des requêtes.
- Docker, CI distante et surveillance prolongée restent à valider. JPMorgan et Citadel Securities n'ont pas été retestés.

## Suite logique

**Nomura professionnels**, puis audit des lacunes des sources déjà intégrées et suivi de candidature. Les priorités figurent dans [ROADMAP.md](ROADMAP.md).

```powershell
.\.venv\Scripts\trading-radar.exe scan --source ubs_professionals
.\.venv\Scripts\trading-radar.exe scan --source hsbc_professionals
.\.venv\Scripts\trading-radar.exe doctor
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src
```
