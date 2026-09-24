# Lot 44 — Telegram et surveillance locale

Livré et installé le **24 septembre 2026**.

## Fonctionnalités

- Alertes d'offres en français, avec dates connues, expérience reconnue,
  décomposition du score et extrait employeur dans sa langue d'origine.
- Commandes privées `/status`, `/help` et `/start`, en lecture seule.
- Signal périodique du collecteur, surveillance indépendante et avis
  d'incident/retour à la normale avec délai de stabilité et espacement.
- Quatrième tâche Windows pour Telegram, avec reprise après échec.
- Lecture bornée des petits corps HTTP refusés dans le dashboard éditable :
  les réponses d'erreur sont fiabilisées sous Windows.

Le classement, le schéma métier et les règles de candidature ne changent pas.
Les tests de commande et de refus HTTP vérifient l'absence d'écritures métier.
La collecte permanente continue normalement à alimenter la base.

## Vérifications

- Paquet Windows non éditable : **2 720 tests réussis**, couverture **96 %**.
  Le passage complet initial avait reproduit deux refus HTTP intermittents ;
  le passage complet final réussit après correction.
- Ruff : 188 fichiers ; mypy : 74 fichiers, scripts inclus.
- [CI du commit b1c408f](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35990767755) :
  **2 720 tests sur chacune des versions Python 3.11, 3.12, 3.13 et 3.14**,
  couverture 96 %. Contrôles statiques réussis.
- Build Docker et restauration synthétique réussis, UID 10001,
  **onze tables identiques** après reprise.
- Autorisation privée, commandes périmées, curseur persistant, erreurs réseau,
  livraison incertaine, limitation des réponses, état corrompu, webhook existant,
  stabilité des incidents et limites UTF-16 couverts par les tests.
- Corps HTTP refusés complets et incomplets testés, avec vérification
  des onze tables métier inchangées.

## Déploiement observé

Sauvegarde vérifiée avant mise à jour à 11 h 03 UTC, contenant 871 offres.
Arrêt des services et attente de la fin effective de leurs processus ;
reconstruction du paquet installé depuis le verrou, puis relance.

Les tâches collecteur, dashboard et Telegram sont en cours d'exécution ;
la tâche de sauvegarde est prête après son précédent succès. Le dashboard
répond HTTP 200. Le signal du collecteur se renouvelle pendant un scan.

À **11 h 07 UTC**, contrôle réel : base accessible, signal âgé de huit secondes,
24 sources suivies dont 21 fraîches, deux en échec récent et une ancienne.
Le menu privé Telegram retourne bien `status` et `help`.
À 11 h 05 UTC, Telegram a accepté une notification automatique d'incident.
Cela confirme l'accusé de livraison API, pas sa lecture par l'utilisateur.
Une commande envoyée par l'utilisateur depuis son téléphone n'a pas encore
été observée pendant cette validation.

Preuves locales ignorées par Git dans `data/windows-service/` :
`features-tests-final.txt`, `deployment-backup.json`,
`telegram-features-smoke.json`, les cinq `ci-lot44-*.json` et les journaux.

## Limites

Les problèmes de sources sont signalés ; ce lot ne répare pas leurs portails.
Les rappels de deadline restent désactivés. Pas de surveillance externe si le PC
est arrêté, pas de sauvegarde distante ni de validation après un vrai
redémarrage. Une observation continue de 24 heures reste à mener.
Voir [le guide Telegram](TELEGRAM-CONTROL.md) et
[l'exploitation Windows](WINDOWS-LIVE.md).
