# Validation du lot 7 — Crédit Agricole CIB et HSBC

16 septembre 2026, Windows / Python 3.14.3. Suite du [lot Société Générale](VALIDATION-LOT6.md).

## Sources livrées

- **Crédit Agricole CIB : 24 offres importées**, après lecture des quatre pages d'un catalogue public de 311 annonces et filtrage des titres. Trois offres obtiennent un score ≥ 70.
- **HSBC étudiants/graduates : 7 offres importées**, parmi 75 programmes publics. Trois programmes Sales & Trading Graduate obtiennent 92, avec un début annoncé en juillet 2027 : Chine continentale, New York et Hong Kong.
- **Douze sources activées pour onze employeurs**. Le périmètre HSBC comprend les programmes Hang Seng du catalogue ; les postes professionnels HSBC restent hors périmètre.
- **Base et CSV : 555 offres enregistrées**, dont **100 avec un score ≥ 70** et 148 avec un score ≥ 55 après recalcul.

Les dates et scores sont issus des fiches collectées ; ils ne garantissent ni l'éligibilité individuelle ni le maintien de l'ouverture d'un poste. Les descriptions complètes et les liens officiels sont conservés pour vérifier chaque offre.

## Imports et répétition

| Source et passage | Reçues | Nouvelles | Modifiées | Fermées | Alertes | Requêtes | Durée |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Crédit Agricole — premier import silencieux | 24 | 24 | 0 | 0 | 0 | 29 | 57 s |
| Crédit Agricole — second import | 24 | 0 | 0 | 0 | 0 | 29 | 57 s |
| HSBC — premier import silencieux | 7 | 7 | 0 | 0 | 0 | 14 | 24 s |
| HSBC — second import | 7 | 0 | 0 | 0 | 0 | 14 | 24 s |

Les premiers imports ajoutent 31 offres. Les seconds passages confirment l'absence de doublon et de modification artificielle dans l'état observé. Le recalcul hors réseau modifie sept explications de score ; une ancienne offre BNP « Trading Analyst - Capital Markets Trainee », dont le contrat est « Stage », quitte le seuil prioritaire. Le total ≥ 70 passe ainsi de 101 après import à 100. Le CSV a été régénéré et ses 555 lignes vérifiées. `doctor` confirme la validité de la base et de la configuration, avec Telegram désactivé et non configuré.

## Contrats, expérience et dates

Chez Crédit Agricole, les champs de type de contrat et d'expérience minimale sont exploités même lorsqu'ils ne figurent pas dans le titre. Les stages sont exclus du classement prioritaire. Les tranches explicites comme « 6 - 10 ans » fournissent leur borne minimale ; cinq ans ou plus déclenchent l'exclusion des postes trop expérimentés. Les valeurs inconnues ne sont pas interprétées. Les descriptions et critères originaux restent conservés.

Le nouveau champ facultatif `minimum_experience_years` est compatible avec les anciennes offres SQLite. Un changement d'expérience minimale ou de contrat crée désormais une version de l'offre ; une répétition identique ne le fait pas. Les règles peuvent être réappliquées hors réseau par `rescore`.

Crédit Agricole affiche une date de mise à jour : elle n'est pas enregistrée comme date de publication. Les dates de début explicitement affichées sont conservées, les deadlines restent inconnues.

HSBC fournit un début dans le catalogue et des dates UTC dans les fiches. Ces dernières servent à la publication et à la deadline ; la date d'ouverture de la carte peut différer de la date de la fiche. Les offres de Chine continentale comportent plusieurs villes, toutes conservées. La première collecte exploratoire a rejeté ces métadonnées répétées avant tout import ; le traitement de plusieurs adresses a été ajouté et testé, puis une collecte complète a réussi.

## Vérifications techniques

- **284 tests réussis**, couverture globale **92 %** ; Crédit Agricole **98 %**, HSBC **97 %**.
- Ruff lint et format validés ; Mypy sans erreur sur **24 modules** ; `pip check` sans conflit.
- Pagination : total, numéro de page, taille, références, doublons, budget de détails et erreurs HTTP testés. Les fragments promotionnels HSBC ne comptent pas comme programmes.
- HSBC : relecture du catalogue après pagination, identifiant stable malgré un changement de libellé d'URL, critères d'éligibilité complets, dates UTC et adresses multiples testés.
- Crédit Agricole : missions, critères, contrat, date de début et expérience minimale testés. Une erreur dans une page empêche tout import partiel de cette source.
- Classement : contrats de stage, maintien des VIE/graduate programmes et exigences structurées d'expérience testés. Historique SQLite testé pour les changements de contrat et d'expérience.
- Parseur HTML partagé avec Société Générale ; suite de régression complète réussie. Aucune nouvelle dépendance.

## Limites et suite

Les deux sources utilisent un filtre local de titres : elles restent partielles et ne ferment pas une offre par absence. Aucune candidature ou notification Telegram n'a été envoyée. Aucun watcher n'a été démarré. Les résultats stockés des autres employeurs ne constituent pas un inventaire actualisé pendant ce lot.

Prochain lot : découverte et intégration de Macquarie et Nomura. Les portails professionnels UBS/HSBC, JPMorgan après son refus HTTP 403, Docker, la CI hébergée et l'exploitation prolongée sur VPS restent à traiter.

Contrats de collecte et portails officiels : [SOURCES.md](SOURCES.md).

## Reproduire

```powershell
.\.venv\Scripts\trading-radar.exe scan --source credit_agricole_cib
.\.venv\Scripts\trading-radar.exe scan --source hsbc_graduates
.\.venv\Scripts\trading-radar.exe rescore
.\.venv\Scripts\trading-radar.exe stats
.\.venv\Scripts\trading-radar.exe doctor
.\.venv\Scripts\python.exe -m pytest --cov=trading_radar
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src
```
