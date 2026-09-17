# Lot 35 — Expérience visible dans le dashboard

Travaux du **17 septembre 2026**, avec trois sous-agents : helper et tests,
interface, audit et régressions indépendantes. L’agent principal a intégré les
résultats, vérifié les parcours dans Edge et actualisé le dashboard local.

## Résultat

Un score élevé peut coexister avec une exigence d’expérience supérieure à deux ans.
Le dashboard affiche désormais le **minimum reconnu** dans chaque ligne et fiche,
avec trois catégories filtrables : **0–2 ans**, **>2 ans**, **non reconnu**.
Les filtres se combinent avec le score, l’entreprise, la recherche et le suivi.

| Offres actives | Minimum 0–2 ans | Minimum >2 ans | Non reconnu | Total |
| --- | ---: | ---: | ---: | ---: |
| Tous scores | 55 | 163 | 594 | 812 |
| Score ≥70 | 21 | 6 | 136 | 163 |
| Score ≥55 | 25 | 29 | 196 | 250 |

Les six offres prioritaires de la catégorie >2 ans demandent trois ans :
Société Générale eFX Trader, Macquarie Intraday Algo Trader, IMC Quantitative
Trading Strategist et trois Flow Traders Digital Assets Trader.

Le calcul reprend le parseur existant et le minimum structuré, en retenant le plus
grand minimum. Un zéro explicite est conservé ; l’indice junior ne devient jamais
un zéro implicite. DRW Floor Trader conserve son score **82**, ses 20 points junior
et un minimum **non reconnu**. Aucun score, règle de classement ou schéma ne change.

Un minimum n’est pas une décision d’éligibilité. La borne basse d’une fourchette
2–5 ans reste deux ans. « Non reconnu » ne signifie ni absence d’exigence ni zéro
expérience. Les préférences, alternatives et formulations inconnues restent soumises
aux limites du parseur. Voir l’[audit indépendant](EXPERIENCE-VISIBILITY-LOT35.md).

## Validation

- **2 068 tests réussis**, dont **56 nouveaux**, couverture **96 %**.
- 46 cas du helper et de l’intégration dashboard, 10 régressions indépendantes.
- Ruff : **159 fichiers** conformes ; mypy : **64 fichiers**, aucune erreur.
- Paquet reconstruit hors réseau depuis `uv.lock`, suite complète exécutée sur
  l’installation non éditable. Aucun ajout de dépendance.
- Un ajustement final du libellé remplace « texte de l’offre » par « annonce »,
  pour inclure les données structurées : paquet reconstruit, 35 tests de rendu
  et parcours navigateur relancés avec succès.

### Parcours navigateur

Edge headless **153.0.4234.32**, via Playwright déjà disponible, dans un profil
temporaire distinct. Le pilote de la session utilisateur n’a pas pu démarrer
(erreur d’ACL du sandbox) ; aucun accès à cette session n’a été utilisé.

Seize contrôles de compteurs réussis sur le HTML exporté, plus les assertions de
détail, pagination, navigation et absence d’erreur JavaScript :

- Score ≥70 et >2 ans : six offres ; entreprise Flow Traders et recherche digital : trois.
- Catégories seules et combinées au score, offres actives/toutes, réinitialisation.
- Pagination remise à la première page après changement du filtre.
- Floor Trader ciblé par recherche et entreprise DRW, minimum non reconnu.
- Ancien jeu de données sans le champ `experience` : résultats classés non reconnus,
  scores conservés ; aucune erreur.
- Captures ordinateur 1440×1000 et mobile 390×844 inspectées. Filtres et détail lisibles,
  aucun débordement du document ou du dialogue ; tableau mobile à défilement horizontal.
- Navigation Offres, Candidatures, Santé et Tendances fonctionnelle.

La première exécution du scénario recherchait Floor Trader sans limiter l’entreprise
et trouvait cinq postes. Le scénario a été précisé avec DRW ; aucune modification
du moteur de recherche n’était nécessaire.

## Données et service local

- **814 offres**, **812 actives**, **163 prioritaires** et **250 pertinentes** conservées.
- Empreintes du contenu ordonné des **11 tables identiques** avant/après.
- Intégrité SQLite valide, aucune violation de clé étrangère ; **CSV inchangé**.
- 814 suivis New, aucun historique de candidature, aucune alerte ; 46 scans conservés.
- Export `data/dashboard/index.html` actualisé avec le paquet installé.
- Ancien processus du dashboard identifié par son exécutable et sa commande, puis
  remplacé sur `127.0.0.1:8765` dans le même mode `--edit-applications`.
- Contrôle Edge du service : HTTP 200, filtre six offres, détail trois ans,
  bouton de suivi disponible, 812 actives après rechargement, aucune écriture.

## Preuves locales

Dans `data/discovery/lot35/` (artefacts ignorés par Git) :

- `before.json`, `preservation.json`, `csv-before.sha256` : préservation.
- `experience-audit.json` : audit indépendant des 814 offres et exemples sourcés.
- `test-results.txt`, `test-results.xml` : suite complète et couverture.
- `export.json`, `ui-results.json`, `live-results.json` : export et parcours.
- `desktop.png`, `mobile.png`, `mobile-detail.png` : captures inspectées.
- `check-ui.cjs`, `check-live.cjs`, `check-preservation.py` : scénarios locaux.
- `preview.pid`, `preview.stdout.log`, `preview.stderr.log` : service local.

Le runtime Docker/VPS et la copie distante restent à valider sur un hôte équipé.
Ce lot n’ajoute pas de collecte ni d’automatisation de candidature.
