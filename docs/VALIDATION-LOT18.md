# Validation du lot 18 — Résolution des alertes incertaines

17 septembre 2026, heure de Paris, Windows / Python 3.14.3. Suite des [rappels conditionnels](VALIDATION-LOT17.md).

## Fonction livrée

Commandes `alerts list/show/history/resolve`, hors réseau et sans initialisation de Telegram. La liste présente par défaut unknown/sending, avec filtre, pagination et résumé global. La consultation associe l'état de livraison aux informations actuelles de l'offre et de la candidature.

Trois décisions opérateur : received pour confirmer une réception, dismiss pour abandonner, retry pour remettre en attente. Elles exigent la révision consultée et un motif non vide. Les transitions autorisées sont bornées ; les états terminaux ne sont pas réouverts par cette interface. Une remise en attente n'envoie rien et peut toujours être supprimée par les contrôles du prochain scan.

La révision et l'état sont lus dans une seule requête SQLite. La résolution relit cette révision sous le verrou commun, empêchant une décision fondée sur un état périmé, même après un retour au même libellé. Modification et historique sont atomiques. Une confirmation de réception ne crée ni nouvelle tentative ni faux timestamp de livraison.

Guide opérateur : [ALERTS.md](ALERTS.md).

## Historique et livraison

La table `alert_history` conserve l'avant/après de chaque transition automatique et décision opérateur, avec timestamp UTC, acteur, décision et motif. Les tentatives augmentent désormais uniquement au passage sending. Les compteurs et états historiques antérieurs sont conservés sans reconstruction arbitraire.

Le client Telegram classe désormais comme incertains les accusés sans booléen `ok`, les réponses non structurées et les statuts de succès inattendus. Une réponse HTTP 200 contenant `{}` ou une liste ne provoque donc plus une reprise aveugle. Les rejets explicites restent retentables.

Le scanner conserve le marquage sending avant appel réseau. Si l'accusé positif est reçu mais que l'enregistrement final échoue, l'alerte reste sending : le passage suivant ne l'envoie pas à nouveau sans décision explicite. Les rappels remis en attente restent soumis à l'activation distincte, au statut de candidature, à la fraîcheur et à la deadline actuelle.

## Migration réelle

Migration additive **SQLite 3 → 4**, ajout de la table et de l'index d'historique. La vérification d'un schéma plus récent intervient désormais avant les opérations de migration.

- Comparaison des nombres de lignes et des empreintes SHA-256 de toutes les tables métier avant/après : **aucune donnée métier modifiée**.
- `PRAGMA quick_check` : **ok** ; `doctor` : configuration et base valides.
- **811 fiches conservées**, **809 actives**, **163 scores ≥ 70**, **247 scores ≥ 55**.
- File d'alertes réelle vide avant et après ; nouvel historique d'alertes vide. Aucun événement synthétique ajouté à la base réelle.
- Statuts de candidature, historiques, scores et timestamps d'observation préservés. Aucun portail rescanné.
- Alertes générales et rappels restent désactivés, Telegram non configuré. Aucun message envoyé et aucun watcher lancé.

Les preuves locales sont dans `data/discovery/lot18/`, ignoré par Git. Les décisions et tentatives synthétiques sont exécutées uniquement sur les bases temporaires des tests.

## Vérification

- **847 tests réussis**, soit **51 supplémentaires**, couverture globale **95 %**.
- Règles de décision **100 %**, CLI alertes **94 %**, stockage **98 %**, notifications **91 %**, scanner **97 %**.
- Ruff valide sur **92 fichiers** ; mypy valide sur **39 modules**.
- Six résolutions unknown/sending, abandon d'un pending, états terminaux, motif invalide, identifiant absent, verrou occupé et révision périmée testés.
- Pagination, consultation sans mutation métier, conservation des anciennes alertes et refus d'un schéma futur sans écriture testés.
- Rollback si l'historique échoue, absence de reprise après échec de persistance de l'accusé positif, compteurs de tentatives et chaîne des états avant/après vérifiés.
- Reprise suivie d'une fermeture d'offre ou d'une candidature Applied : aucune livraison simulée. Réactivation des rappels nécessaire, même après retry.
- Réponses Telegram mal formées, booléens invalides, statuts 201/204/302/500/503 et rejets explicites testés avec transport HTTP simulé.

## Limites et suite logique

Une reprise manuelle après un résultat inconnu peut créer un doublon ; le logiciel n'inspecte pas Telegram pour décider si le premier message existe. Le motif documente la décision et ne prouve pas une non-livraison. Les informations de l'offre affichées sont actuelles, pas une archive du contenu exact du message historique.

Prochaine étape : **sauvegardes SQLite cohérentes et restauration vérifiée**, incluant offres, candidatures et historiques d'alertes, puis contrôle de l'exploitation Docker/VPS. La livraison Telegram réelle et les tests prolongés restent à valider séparément.
