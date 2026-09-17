# Validation du lot 16 — Suivi des candidatures

17 septembre 2026, heure de Paris, Windows / Python 3.14.3. Suite de l'[audit de fraîcheur](VALIDATION-LOT15.md).

## Fonction livrée

Les commandes `applications list`, `show`, `update` et `history` rendent utilisable le schéma de suivi prévu par le master prompt. Les douze statuts sont disponibles, avec date de candidature, recruteur, notes, prochaine action et date d'action. Les commandes fonctionnent sans réseau ni initialisation de Telegram. Elles enregistrent les décisions de l'utilisateur ; elles n'effectuent aucune candidature.

L'édition modifie uniquement les champs fournis ; `--clear` permet un effacement explicite. Les dates sont des jours calendaires ISO stricts et aucune date de candidature n'est déduite d'un statut. Une prochaine action datée doit avoir un libellé. Les changements de statut restent libres pour permettre les corrections. La liste permet le filtrage par statut ou date d'action inclusive et la pagination.

Chaque changement effectif enregistre l'avant, l'après et l'heure UTC dans `application_history`. Écriture et historique sont atomiques et utilisent le verrou du scanner. Une répétition identique ne crée pas d'historique supplémentaire. Les scans et les fermetures/réouvertures préservent les informations personnelles. Le statut `Closed` du suivi n'est pas l'état d'ouverture de l'offre publique.

La migration SQLite **2 → 3** ajoute uniquement la table et l'index d'historique ; les suivis existants sont conservés. Aucun passé n'est inventé. Le CSV garde les colonnes précédentes dans leur ordre et ajoute l'identifiant et les cinq champs de suivi manquants. Les textes pouvant être interprétés comme formules sont neutralisés dans l'export, sans modification des valeurs SQLite.

Guide complet et exemples : [APPLICATIONS.md](APPLICATIONS.md). Les éditions ne rafraîchissent pas automatiquement le CSV : utiliser `export`, ou attendre le prochain scan.

## Sources actualisées

| Source | Premier passage : reçues | Nouvelles | Modifiées | Fermées | Durée source |
| --- | ---: | ---: | ---: | ---: | ---: |
| Goldman professionnels | 68 | 3 | 0 | 0 | 222,0 s |
| Goldman campus | 30 | 0 | 0 | 0 | 119,2 s |
| Jane Street | 230 | 2 | 2 | 0 | 3,1 s |

Les deux sources Goldman partagent 125 requêtes HTTP ; Jane Street utilise deux requêtes. **Cinq nouvelles fiches** sont conservées. Les deux nouvelles fiches Jane Street sont des fonctions de cybersécurité et de facilities, avec score nul. Leur catalogue Greenhouse historique est complet ; le filtrage d'opportunités intervient au classement.

L'audit passe de **21 sources récentes et trois anciennes** à **24 sources récentes**, au seuil de 24 heures ; quatre sources restent désactivées. Ce résultat est une mesure ponctuelle, aucun watcher n'est lancé. JPMorgan et Citadel Securities n'ont pas été retestés.

Goldman professionnels conserve 73 fiches dont 68 revues. Les cinq absentes restent conservées, sa recherche étant partielle. Goldman campus conserve 30 fiches toutes revues. Jane Street conserve 232 fiches dont 230 revues ; les deux absences relèvent de la règle existante des deux inventaires complets consécutifs.

Le second passage reçoit les mêmes 98 fiches Goldman et 230 Jane Street, avec **zéro nouvelle et zéro modification**. Goldman ne ferme rien. Jane Street ferme **IT Operations Engineer** et **Linux Engineer**, deux fiches à score nul absentes des deux inventaires complets. Durées : 222,4 secondes pour les deux sources Goldman et 3,4 secondes pour Jane Street ; toujours 125 et deux requêtes, aucune alerte.

## Correction de pertinence

Les nouvelles fiches Goldman [Credit Risk Analyst, Salt Lake City](https://higher.gs.com/roles/179693) et [Credit Risk Associate, Salt Lake City](https://higher.gs.com/roles/179692) avaient respectivement 74 et 62 points. Les descriptions appartiennent explicitement à la Risk Division : analyse des contreparties, fixation de limites de crédit et revue du risque des transactions. La mention Global Markets ne suffit pas à en faire des rôles de trading.

L'exclusion ciblée `risk credit risk` s'applique à cette structure de titre de département, également présente sur des fiches plus anciennes. Les intitulés Credit Trading Analyst et Credit Risk Trader restent acceptés par les tests de contre-exemples. Les scores sont recalculés hors réseau après le second scan ; aucune offre n'est supprimée.

Le recalcul actualise le classement de **cinq fiches**. Bilan final : **811 fiches conservées**, **809 actives**, **163 scores ≥ 70** et **247 scores ≥ 55**. Les 811 lignes du CSV concordent avec SQLite ; ses 18 colonnes incluent les nouvelles informations de suivi.

## Tests et limites

- **711 tests réussis**, soit 43 supplémentaires ; couverture globale **94 %**, modèle de candidature **100 %**, commandes de suivi **95 %**, stockage **96 %**.
- Ruff valide sur **85 fichiers** ; mypy valide sur **34 modules**. `doctor` confirme configuration et SQLite valides, alertes désactivées et Telegram non configuré. Aucune alerte en base.
- Tests des douze statuts, champs omis, effacement, dates invalides, absence de date inventée, limites de texte, IDs inconnus et verrou occupé.
- Historique avant/après, opérations identiques, rollback si l'historique échoue, migration depuis le schéma 2 avec notes existantes.
- Conservation du suivi pendant mise à jour, fermeture et réouverture ; séparation entre statut personnel et état de l'offre.
- Parcours CLI sans Telegram, filtres par statut/date, pagination, isolation démo et CSV enrichi avec protection contre les formules.
- Les vérifications modifient uniquement des bases temporaires. Les 811 suivis de la base réelle restent à `New` et leur historique est vide : aucune décision de candidature n'a été inventée.

Les rappels automatiques, l'extraction de nouvelles deadlines, le dashboard, l'import CSV et la synchronisation externe restent à construire. Les statuts n'agissent pas encore sur les alertes générales d'offres ; les futurs rappels devront vérifier le suivi avant envoi. Les dates et champs libres effacés restent dans l'historique local. Aucun envoi, aucune alerte et aucune candidature automatique réalisés pendant ce lot.

Rapports locaux : `data/discovery/lot16/`, ignoré par Git. Aucune nouvelle dépendance. Docker, CI distante et surveillance prolongée restent à valider.

## Suite logique

Compléter les échéances : extraire uniquement les deadlines explicites et fiables, proposer leur consultation, puis préparer les rappels J−7/J−3/J−1 avec suppression selon le statut de candidature. L'état de fraîcheur sert désormais de point de contrôle avant toute extension de couverture.
