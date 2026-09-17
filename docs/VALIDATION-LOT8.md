# Validation du lot 8 — Macquarie et Nomura campus

16 septembre 2026, Windows / Python 3.14.3. Suite du [lot Crédit Agricole CIB et HSBC](VALIDATION-LOT7.md).

## Résultat

- **Macquarie : 17 offres importées**, après parcours de dix pages de la recherche publique « trading » (87 résultats) et filtre local de titres.
- **Nomura campus : 12 offres importées**, parmi les 44 opportunités du tableau étudiant officiel.
- **Base et CSV : 584 offres enregistrées**, dont **103 avec un score ≥ 70** et 151 avec un score ≥ 55.
- **Quatorze sources activées pour treize employeurs**. Goldman Sachs conserve ses deux sources professionnelle et campus ; Nomura est couvert uniquement par son tableau campus.

Les 12 offres Nomura sélectionnées sont actuellement des stages, y compris les « Graduate Internship ». Elles sont toutes exclues du classement prioritaire. Trois offres Macquarie franchissent le seuil de 70 : Institutional Cash Equity Sales Trader, Foreign Exchange and Rates Sales and Trading Associate, Intraday Algo Trader. Aucune n'est confirmée comme programme graduate 2027 ; l'offre Intraday demande au moins trois ans et son score junior est nul. Le seuil reste un classement de proximité, à lire avec les exigences de chaque fiche.

## Imports et répétition

| Source et passage | Reçues | Nouvelles | Modifiées | Fermées | Alertes | Requêtes | Durée |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Macquarie — premier import silencieux | 17 | 17 | 0 | 0 | 0 | 28 | 56 s |
| Nomura — premier import silencieux | 12 | 12 | 0 | 0 | 0 | 14 | 123 s |
| Macquarie — second import | 17 | 0 | 0 | 0 | 0 | 28 | 56 s |
| Nomura — second import | 12 | 0 | 0 | 0 | 0 | 14 | 123 s |

Les seconds passages ne créent aucun doublon ni modification artificielle. Nomura a répondu lentement mais sans erreur ni dépassement du budget de collecte. Le CSV contient 584 lignes d'offres ; `doctor` confirme la validité de la base et de la configuration, avec Telegram désactivé et non configuré.

## Qualité du classement

Macquarie publie parfois le niveau d'expérience uniquement dans les métadonnées. Le nouveau champ facultatif `seniority_hint` conserve une indication junior ou senior explicite. « Senior » et « Mid-senior » sans niveau inférieur entraînent l'exclusion ; « Junior » contribue au score junior. Les combinaisons ambiguës de niveaux restent non interprétées. Les titres seniors et les exigences d'expérience continuent de prévaloir sur un indice junior.

Les tranches d'expérience sont lues dans la rubrique « What you offer » : le poste « Rates Trader Associate » demande 6–10 ans et est donc exclu, malgré son titre Associate. Les années citées dans la présentation du desk ne deviennent pas une exigence candidat. Les contrats et cet indice de séniorité sont conservés dans les payloads SQLite et leurs changements sont historisés ; les anciennes offres restent compatibles.

Le poste « Operator Commodities Trading Associate » concerne les mouvements de métaux, le transport, le stockage et la livraison. Son intitulé précis est ajouté aux exclusions de fonctions opérationnelles. Le recalcul hors réseau n'a modifié aucun score parmi les offres déjà enregistrées.

## Collecte et dates

Macquarie : le filtre saisi, le total, le numéro et la taille de chaque page sont vérifiés. Références, titre, lieu, contrat, missions et exigences sont contrôlés avant import. Le libellé générique « Date » n'est pas présenté comme une date de publication originale ; début d'emploi et deadline restent inconnus sans preuve explicite vérifiée.

Nomura : le nombre de lignes doit correspondre au total du tableau, les identifiants de carte et de fiche doivent correspondre. La route publique sans préfixe variable de contexte a été vérifiée et sert d'URL stable. Les champs anti-CSRF des formulaires ne sont ni utilisés ni stockés. Le formulaire de candidature n'est jamais soumis. La deadline du tableau n'indique pas de fuseau ; aucune échéance précise n'en est déduite. Les dates présentes dans la description sont conservées dans leur contexte.

Les deux collectes restent filtrées et ne ferment aucune offre par absence. Les résultats des autres employeurs n'ont pas été actualisés pendant ce lot ; le nombre stocké ne constitue pas un inventaire garanti de postes encore ouverts.

## Vérifications

- **333 tests réussis**, couverture globale **93 %** ; Macquarie **95 %**, Nomura **95 %**.
- Ruff lint et format validés ; Mypy sans erreur sur **26 modules**. Aucune dépendance ajoutée.
- Pagination Macquarie : filtre perdu, page courte, numéro incorrect, total changeant, doublon, erreur HTTP et limites testés ; fusion de plusieurs recherches sans doublon.
- Nomura : total/table incohérents, colonnes modifiées, références contradictoires, URL hors périmètre, détail incomplet et erreur tardive testés. Deux préfixes de contexte produisent la même identité et la même URL stable.
- Descriptions et critères requis conservés ; niveau d'expérience, tranches d'années et exclusions testés. Régression du stockage et du classement réussie.
- Aucun watcher démarré et aucune candidature ou notification Telegram envoyée.

## Périmètre restant et suite

Le portail professionnel Nomura SuccessFactors a été identifié comme une source distincte, sans activation. Les portails professionnels UBS/HSBC et JPMorgan après son refus HTTP 403 restent également à traiter. Docker, CI hébergée et exploitation prolongée sur VPS restent à vérifier.

Prochaine étape : **Citadel Securities et Optiver**, puis les autres sociétés de trading de la phase 2. Les contrats et liens officiels des nouvelles sources sont détaillés dans [SOURCES.md](SOURCES.md).

## Reproduire

```powershell
.\.venv\Scripts\trading-radar.exe scan --source macquarie
.\.venv\Scripts\trading-radar.exe scan --source nomura_campus
.\.venv\Scripts\trading-radar.exe rescore
.\.venv\Scripts\trading-radar.exe stats
.\.venv\Scripts\trading-radar.exe doctor
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src
```
