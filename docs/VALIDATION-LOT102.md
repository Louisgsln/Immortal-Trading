# Lot 102 — Diagnostic des lanceurs et fichiers PID fiables

Livraison du 6 octobre 2026. Une nouvelle commande examine les processus locaux
qui utilisent les points d'entrée connus du radar :

```console
trading-radar runtime
```

Sous Linux, elle lit `/proc`. Sous Windows, elle interroge CIM et les tâches
`Immortal-Trading-*` par PowerShell, sans modifier ces tâches. Le résultat donne
PID, rôle, parent et configuration lorsqu'elle est identifiable. Les lignes de
commande et arguments privés ne sont jamais recopiés dans le rapport.

Les wrappers `uv`/`py` et les chaînes parent-enfant d'une même configuration
ne deviennent pas des collecteurs indépendants. Deux arbres de processus watch
ou Telegram sur la même configuration sont signalés. Une configuration inconnue
produit une demande de vérification, pas une affirmation de doublon. Plusieurs
tâches connues pour un même rôle sont aussi signalées pour examen.

Le périmètre reste explicite : les appels importés depuis d'autres scripts,
les noms de tâches différents et les ordonnanceurs Unix ne sont pas tous
identifiables par cette commande. Une lecture incomplète ou indisponible conserve
cet état ; elle ne prouve pas l'absence de collecteurs. Aucun processus n'est
lancé, arrêté ou tué, aucun message n'est envoyé, aucune base n'est créée.

Le heartbeat inclut désormais le PID du collecteur. Le service Windows supprime
son fichier PID à l'arrêt, seulement s'il lui appartient encore ; une tentative
de lancement en doublon ne supprime pas celui du service actif. Un heartbeat ou
fichier PID isolé ne prouve pas l'unicité d'un service.

Validation ciblée : **84 tests réussis**, couvrant diagnostic, commandes Telegram,
verrous de service et heartbeat. Extraction des tâches Windows vérifiée par
contrat simulé ; lecture Linux exécutée dans le cloud, sans collecteur connu
détecté. L'état du PC Windows et son ordonnanceur restent non vérifiés.

Validation globale de la version finale des lots 100–102 :

- **4 803 tests Python réussis**, aucun échec, erreur ou test ignoré, répartis
  sur quatre processus isolés. Couverture combinée : **96 %**.
- Ruff, formatage et mypy réussis sur les **101 modules applicatifs** ;
  **11 tests JavaScript** réussis et syntaxe du dashboard vérifiée.
- Chromium exécuté avec requêtes réseau bloquées : filtre des offres expirées,
  badges, conservation des candidatures, périodes de début, négation du visa,
  compteurs de sélection et texte HTML importé inerte vérifiés.
- Wheel construite ; les **106 fichiers applicatifs** extraits correspondent
  octet pour octet aux sources validées. SHA-256 :
  `f48321625d24a34ebdfc3cad378fef4f280172c606a7b86f72001dff817adc78`.
- Exercice de reprise lancé depuis ce paquet : huit offres synthétiques,
  deux collectes sans doublon, sauvegarde vérifiée, restauration de **11 tables
  identiques**, dashboard, historique et rétention opérationnels.

Les lots 99, 100 et 101 sont publiés sur `main`. Leurs vérifications GitHub Actions
étaient encore en cours au moment de ce bilan ; les résultats locaux ci-dessus
ne les remplacent pas. Le lot 102 est livré après ces contrôles locaux.

L'exercice de reprise est un parcours local du paquet, pas une exécution Docker.
Aucun déploiement Windows n'est annoncé. La prochaine vérification opérationnelle
exige l'accès à l'instance Windows : inventaire réel des lanceurs, sauvegarde,
installation puis contrôle de la collecte et des alertes sur cette instance.
