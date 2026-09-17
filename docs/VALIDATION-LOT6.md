# Validation du lot 6 — Société Générale

16 septembre 2026, Windows / Python 3.14.3. Suite du [lot UBS](VALIDATION-LOT5.md).

## Résultat

- **33 offres Société Générale importées** depuis les répertoires publics français et anglais, avec descriptions et profils requis.
- Découverte : 434 cartes françaises, 637 anglaises et 49 références communes, soit **1 022 références distinctes** avant filtre local de titres.
- Base et CSV après recalcul : **524 offres enregistrées**, dont **95 avec un score ≥ 70**. Société Générale contribue 12 de ces 95 offres.
- **Dix sources activées pour neuf employeurs** : Jane Street, Deutsche Bank, Morgan Stanley, Citi, Barclays, Goldman Sachs (deux sources), BNP Paribas, UBS et Société Générale.

Les comptes décrivent la base locale et le classement automatique. Les sources filtrées ne ferment pas les offres par absence : 524 offres enregistrées ne signifie pas 524 postes dont l'ouverture actuelle est garantie. Les autres sources n'ont pas toutes été relues pendant ce lot.

## Vérifications réseau

| Passage Société Générale | Reçues | Nouvelles | Modifiées | Fermées | Alertes | Requêtes | Durée |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Premier import silencieux | 33 | 33 | 0 | 0 | 0 | 36 | 71 s |
| Second passage | 33 | 0 | 0 | 0 | 0 | 36 | 71 s |

Les deux passages complets ont réussi. Le second confirme l'absence de doublon et de modification artificielle dans l'état observé, notamment pour les références présentes dans les deux langues.

Portails vérifiés : [répertoire français](https://careers.societegenerale.com/fr/Technical/toutes-les-offres) et [répertoire anglais](https://careers.societegenerale.com/en/Technical/all-job-offers). Les appels respectent l'espacement du client HTTP et ses contrôles robots. Aucun appel OAuth n'est nécessaire.

## Qualité des données et classement

- L'anglais est préféré de manière déterministe pour une référence commune aux deux répertoires.
- Le titre visible est utilisé ; le titre JSON-LD ajoute parfois une division qui pourrait provoquer une exclusion injustifiée.
- Missions et profil requis doivent être présents et non vides. Référence, URL canonique, publication et lieux sont contrôlés avant import.
- Le début d'emploi est extrait de son libellé explicite. `validThrough` n'est pas une deadline fiable sur les fiches inspectées et reste non interprété.
- « V.I.E. » est reconnu comme « VIE » et « structuration » comme « structuring ».
- Le poste « Bernstein - Trading Application Support » avait obtenu 77. Son descriptif confirme une fonction IT de support, de gestion des incidents et de déploiement. L'exclusion des titres « application support » ramène son score à 0 ; les développeurs intégrés aux desks conservent leurs règles propres.
- Le recalcul hors réseau a modifié un score, sans nouvelle observation ni alerte, et actualisé le CSV. Le total prioritaire passe ainsi de 96 à 95 après les scans.

## Contrôles automatisés

- **227 tests réussis**, couverture globale **91 %**, connecteur Société Générale **94 %**.
- Ruff lint et format validés ; Mypy sans erreur sur **21 modules**.
- Tests du connecteur : fusion des langues, comptes et cartes incohérents, URLs hors périmètre, références et dates contradictoires, profils vides, limites de détails, refus HTTP et rejet d'un import partiel.
- Tests du score : V.I.E., structuration française et exclusion du support applicatif malgré une description contenant des mots-clés de trading.
- `doctor` : base et configuration valides ; Telegram désactivé et non configuré. Aucun watcher démarré dans ce lot.

## Limites et suite

Le filtre de titres ne couvre pas tous les métiers du groupe ; stages et postes hors cible peuvent être stockés puis exclus par le score. Les deadlines restent inconnues lorsqu'aucune preuve fiable ne permet de les extraire. La collecte est ponctuelle, sans surveillance continue déployée.

Prochaine étape : vérifier et intégrer les portails publics Crédit Agricole CIB et HSBC. JPMorgan reste désactivé après HTTP 403 ; le portail UBS professionnel, Docker, la CI hébergée et l'exploitation prolongée sur VPS restent à vérifier.

## Reproduire

```powershell
.\.venv\Scripts\trading-radar.exe scan --source societe_generale
.\.venv\Scripts\trading-radar.exe rescore
.\.venv\Scripts\trading-radar.exe stats
.\.venv\Scripts\trading-radar.exe doctor
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src
```
