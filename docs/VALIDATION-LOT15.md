# Validation du lot 15 — Fraîcheur et couverture Workday

17 septembre 2026, heure de Paris, Windows / Python 3.14.3. Suite du [lot Nomura professionnels](VALIDATION-LOT14.md).

## Fonction livrée

`trading-radar audit` produit un rapport JSON hors réseau, avec un seuil configurable de fraîcheur (24 heures par défaut) et un export facultatif. Lecture SQLite `mode=ro` dans une transaction cohérente : aucune observation modifiée, aucune migration, aucune création de base absente, aucune initialisation de Telegram. La sortie ne peut pas remplacer le fichier SQLite ni ses fichiers WAL/SHM.

Chaque source expose son dernier succès/échec, son âge, son dernier volume, sa durée moyenne historique, son intervalle configuré, ses requêtes et ses nombres de fiches revues ou non revérifiées. Les identités multiples d'une fiche sont réunies par source. Dates invalides ou futures : état inconnu ; source désactivée : état désactivé, avec motif. Les états de sources retirées de la configuration sont également signalés. Le rapport est informatif : les sources anciennes ou en échec n'entraînent pas à elles seules un code retour non nul.

## Fraîcheur observée

| Mesure, seuil 24 h | Avant | Après actualisation Workday |
| --- | ---: | ---: |
| Sources récentes | 17 | 21 |
| Sources anciennes | 7 | 3 |
| Sources désactivées | 4 | 4 |

Les quatre banques Workday dataient d'environ 47 heures. Les trois sources encore anciennes sont **Goldman Sachs professionnels, Goldman campus et Jane Street**, non rescannées dans ce lot. Il y a toujours **24 sources activées pour 20 employeurs**.

Après actualisation, Deutsche Bank conserve 25 fiches dont 22 revues ; Morgan Stanley 21 dont 20 revues. Leurs quatre anciennes fiches absentes ne sont pas déclarées fermées, car les recherches restent partielles. BNP conserve également huit fiches non revérifiées au seuil de 24 h malgré une source récente. Une source récente ne garantit donc ni la fraîcheur de tout son historique ni l'ouverture de toutes ses offres. Aucun watcher n'est lancé ; les intervalles configurés ne sont pas une cadence réellement mesurée.

## Couverture des recherches

Le script `scripts/audit_workday.py` compare les recherches publiques avec le client HTTP habituel, les règles robots, deux secondes entre requêtes et les budgets existants. Il ne modifie pas SQLite. Les nombres suivants correspondent aux titres retenus localement après pagination complète de chaque requête réussie.

| Source | Trading | Trader | Structuring | Repo | Securities Finance | Suppléments distincts hors Trading |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Barclays | 22 | 17 | 22 | 24 | 0 | 6 |
| Deutsche Bank | 22 | 22 | 17 | 12 | 8 | 7 |
| Morgan Stanley | 20 | 6 | 10 | 8 | 8 | 3 |
| Citi | 57 | 57 | Limite dépassée | Non mesuré | Non mesuré | 0 pour Trader seulement |

Les **16 suppléments évalués ont tous un score nul** selon les critères actuels. Leurs descriptions comprennent notamment des stages Capital Markets, l'investment banking, le financement d'infrastructure, un développeur sans preuve suffisante de rôle intégré au trading et des fonctions hors cible. Il ne s'agit pas d'une preuve d'exhaustivité : le filtrage et le classement peuvent encore manquer des postes pertinents.

Coût de l'audit : Barclays 39 requêtes HTTP, Deutsche Bank 87, Morgan Stanley 85, Citi 122. Citi `trading` renvoie 1 207 résultats bruts ; `trader` 1 165 sans titre supplémentaire retenu. `structuring` dépasse la limite de 1 999 : l'audit de Citi est explicitement en échec/incomplet, sans import, et les deux termes suivants ne sont pas parcourus. Cette erreur exploratoire ne marque pas en échec la source opérationnelle dont la requête Trading reste valide.

**Décision : conserver `search_terms: [trading]` pour les quatre banques**, sans relever les budgets ni ajouter de coût permanent sans gain démontré. Le collecteur détecte désormais un même chemin présentant des titres différents entre deux requêtes et interrompt la source avant import. La déduplication normale entre requêtes est conservée.

## Premier passage d'actualisation

| Source | Reçues | Nouvelles | Modifiées | Fermées | Durée |
| --- | ---: | ---: | ---: | ---: | ---: |
| Barclays | 22 | 2 | 0 | 0 | 56,8 s |
| Deutsche Bank | 22 | 3 | 1 | 0 | 76,8 s |
| Morgan Stanley | 20 | 4 | 1 | 0 | 75,3 s |
| Citi | 57 | 3 | 1 | 0 | 238,4 s |

Total : **121 fiches revues, 12 nouvelles et trois modifiées**, en 225 requêtes. Ces nouvelles fiches proviennent de l'actualisation de Trading après environ 47 heures ; elles ne sont pas un gain des requêtes supplémentaires. Les 16 fiches exploratoires ne sont pas importées.

Exemples nouvellement observés : [Sales, Trading and Structuring Graduate Programme 2027, Zurich](https://barclays.wd3.myworkdayjobs.com/External_Career_Site_Barclays/job/Zurich-Beethovenstrasse-19/Sales--Trading-and-Structuring-Graduate-Programme-2027-Zurich_JR-0000132730), **96/100**, et IB – GEM Trader – Analyst, **90/100**, à [Kuala Lumpur](https://db.wd3.myworkdayjobs.com/DBWebsite/job/Kuala-Lumpur-Menara-IMC/IB---GEM-Trader---Analyst_R0450475-1) et [Hong Kong](https://db.wd3.myworkdayjobs.com/DBWebsite/job/Hong-Kong-Intl-Commerce-Ctr/IB---GEM-Trader---Analyst_R0450486). Ces deux derniers postes ont des références distinctes. Les scores servent au tri ; éligibilité, missions et modalités de début restent à vérifier. Aucune date précise de début n'est inventée.

## Correction de classement

Le poste Citi [Electronic Execution Sales Trading Desk Head](https://citi.wd5.myworkdayjobs.com/2/job/London--United-Kingdom/Sales-Trading-Desk-Head_26983763) avait un score de 75. La description indique une responsabilité de co-direction EMEA et exige un niveau Director ou équivalent. L'exclusion de séniorité `desk head` ramène ce score à zéro ; le recalcul des 806 fiches modifie **un seul score**. Un analyste qui rapporte au desk head dans sa description reste éligible au classement : l'exclusion cible l'intitulé du poste.

## Vérifications

- **Second passage stable sur les quatre sources** : 121 fiches reçues, zéro nouvelle, zéro modification, zéro fermeture et zéro alerte ; 225 requêtes, 239,9 secondes. Aucun doublon créé.
- **SQLite et CSV : 806 fiches conservées**, dont **164 scores ≥ 70** et **249 scores ≥ 55**, après correction Desk Head. Aucune alerte en base ; aucun message envoyé.
- **668 tests réussis**, soit 37 supplémentaires ; couverture globale **94 %**, module d'audit **100 %**.
- Ruff : **82 fichiers** ; mypy : **32 modules**, sans erreur.
- Seuil exact, dates invalides/futures/sans fuseau, succès après échec, sources désactivées ou retirées, observations multiples, base absente/corrompue et refus effectif des écritures SQLite testés.
- Déduplication Workday entre requêtes et interruption en cas de titre contradictoire ; exclusion Desk Head et contre-exemple junior testés.
- `doctor` : configuration et SQLite valides, alertes désactivées, Telegram non configuré.

Les rapports locaux sont dans `data/discovery/lot15/` (ignorés par Git). Aucun changement de schéma ou de dépendance. Docker, CI distante et surveillance prolongée restent à valider.

## Suite logique

Actualiser Goldman professionnels, Goldman campus et Jane Street, puis compléter le cycle de candidature : édition des statuts, notes et prochaines actions. Poursuivre séparément l'audit des titres techniques manqués et des recherches Citi plus ciblées avant tout élargissement permanent.

```powershell
.\.venv\Scripts\trading-radar.exe audit --output data/freshness.json
.\.venv\Scripts\trading-radar.exe audit --max-age-hours 48
.\.venv\Scripts\trading-radar.exe scan --source workday
.\.venv\Scripts\python.exe scripts/audit_workday.py
```
