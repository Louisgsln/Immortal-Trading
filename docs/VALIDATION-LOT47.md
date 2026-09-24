# Lot 47 — Classement et expérience reconnue

Déployé le **24 septembre 2026**, commit applicatif `e8d57e4`.

## Résultat

Quatre exigences textuelles auparavant inconnues sont reconnues : Deutsche Bank
3 et 1 ans, Goldman Sachs 0 et 2 ans. Les preuves et limites de l'extension sont
dans [EXPERIENCE-AUDIT-LOT47.md](EXPERIENCE-AUDIT-LOT47.md).

Un seul score change, **75 → 70**, par retrait de cinq points de compatibilité
junior sur l'offre exigeant trois ans. Le seuil d'alerte reste 70 et les règles
d'éligibilité ne changent pas. Aucune nouvelle alerte n'est envoyée par le recalcul.

## Vérification et application

- **2 849 tests réussis** sur le paquet Windows installé non éditable,
  couverture **96 %**, dont 46 nouveaux cas.
- Ruff : 193 fichiers ; mypy : 70 modules applicatifs.
- [CI du commit e8d57e4](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36006485964) :
  **2 849 tests réussis sur chacune des versions Python 3.11 à 3.14**,
  couverture 96 %, contrôles Ruff/mypy réussis. Build Docker et reprise
  synthétique sous UID 10001 validés, onze tables restaurées identiques.
- Audit de l'ancien et du nouveau programme sur la même sauvegarde restaurée :
  872 offres, quatre minima précisés, un seul score changé.
- Répétition sur la copie restaurée, puis sauvegarde de la base active avant
  installation et recalcul dans une transaction verrouillée.
- En production : **871 lignes d'offres strictement inchangées**, huit tables
  préservées, dont candidatures, alertes, sources et scans. Un événement de
  recalcul et une entrée de score ajoutés ; historique antérieur conservé.
- Dates de collecte et contenu employeur conservés. Second passage sans effet
  sur les onze tables ; intégrité SQLite et relations vérifiées.

## Vérification du service installé

Les trois services ont redémarré. À **13 h 35 UTC**, le serveur local retourne
HTTP 200 ; les données servies au dashboard contiennent les quatre nouveaux
minima et le score corrigé. Le CSV contient 872 lignes et le score 70 attendu.
L'export HTML a été régénéré ; le format Telegram produit trois ans et 70/100.
Le contrôle Telegram est une génération locale, sans réexpédition de l'offre.

Le signal du collecteur est récent. Le récapitulatif quotidien reste activé à
09:00 Paris. À cet instant, le dashboard compte **864 offres actives,
257 pertinentes et 175 prioritaires**. Ces nombres évoluent avec la collecte.

**22 sources sur 24 sont fraîches** : Nomura campus a un échec récent et BNP
Paribas une collecte ancienne. Ce lot ne répare pas ces connecteurs. Les anciens
incidents DB/UBS ne doivent pas être confondus avec l'état de ce contrôle.

Preuves privées ignorées par Git dans `data/windows-service/` :
`lot47-tests.txt`, `lot47-tests.xml`, `lot47-impact.json`, sauvegardes et rapports
de restauration, `lot47-rehearsal-proof.json`, `lot47-production-proof.json`,
`lot47-dashboard-export.json` et `lot47-smoke.json`.
Les cinq journaux CI sont conservés dans les `ci-lot47-*.json` locaux.

## Suite recommandée

1. Diagnostiquer les échecs des sources encore observés, dans le respect des
   accès publics autorisés ; mesurer les retours à un état normal.
2. Ajouter le suivi de candidature depuis Telegram avec confirmation et
   historique, pour marquer une offre à traiter, envoyée ou écartée.
3. Vérifier une copie de sauvegarde sur un autre stockage et compléter la
   surveillance extérieure du PC. Un serveur autonome reste une évolution
   possible si l'on souhaite supprimer la dépendance au PC allumé.

La provenance Nomura et les audits des rôles hybrides restent également dans
la feuille de route. Aucun matching CV ni candidature automatique ajouté ici.
