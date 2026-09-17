# Lot 31 — Aperçu de collecte avant import

Travaux du **17 septembre 2026**, avec un sous-agent pour le moteur et ses tests.
La limite de session a empêché le lancement d'un deuxième sous-agent. L'agent
principal a intégré la commande, les tests CLI et le scénario de reprise,
effectué la mesure réelle puis validé l'ensemble.

## Fonction livrée

- `scan --dry-run`, combinable avec `--company`, `--source` ou `--demo`.
- Copie SQLite cohérente incluant le WAL, archive vérifiée puis restauration
  temporaire. Base active jamais ouverte comme dépôt d'écriture.
- Simulation du scanner existant : changements, scores et activité avant/après,
  mêmes règles de collecte, déduplication et fermetures.
- Aucune construction du notifier Telegram, aucun export, alertes et rappels
  désactivés dans la copie de configuration.
- Rapport JSON et codes de sortie explicites : succès, source indisponible,
  erreur globale ou filtre sans source. Les identifiants nouveaux sont temporaires.
- Limites : 5 000 offres, 10 000 nouveaux événements, taille de payload bornée.
  Une erreur globale supprime tout aperçu partiel ; une erreur de source conserve
  les résultats des autres sources sous le statut `incomplete`.

Guide complet et limites : [SCAN-PREVIEW.md](SCAN-PREVIEW.md). Un import ultérieur
relit les sources ; le JSON d'aperçu n'est pas un plan d'import réutilisable.

## Exercice réel Flow Traders

Commande exécutée sur le paquet installé :

```powershell
data/validation-lot20-venv/Scripts/python.exe -m trading_radar scan --dry-run --source flow_traders
```

Une première tentative dans le réseau restreint a produit `incomplete` avec
quatre tentatives de transport échouées. La lecture publique ensuite autorisée
a réussi en deux requêtes, règles robots comprises : **10 offres reçues,
0 ajout, 0 modification, 0 fermeture, 0 alerte**. Aucune restriction du portail
n'a été contournée. Le périmètre reste celui des titres retenus par le connecteur.

Le scan simulé n'a pas été importé et n'a donc pas rafraîchi les dates d'observation
de la base active. Un succès de cet aperçu n'atteste pas la fraîcheur des autres
sources.

## Préservation et validation

- **Onze tables identiques avant/après**, compteurs et SHA-256 comparés ; intégrité
  SQLite valide et aucune erreur de relation.
- Toujours **813 offres, 811 actives, 163 scores actifs ≥70 et 249 ≥55**, 45 scans
  métier. Candidatures, alertes et historiques préservés.
- Empreintes du CSV métier et du dashboard HTML inchangées.
- **1 884 tests réussis**, soit **35 nouveaux**, couverture Python **96 %**.
  Parmi eux : 29 tests du moteur et six cas CLI ; le scénario de reprise existant
  vérifie aussi les aperçus avant création et après ajout d'historiques synthétiques.
- Ruff : **148 fichiers** conformes ; mypy : **61 fichiers**, sans erreur.
- Suite complète sur une installation non éditable reconstruite hors réseau
  depuis `uv.lock`. Aucune dépendance ni migration ajoutée.

Les tests couvrent notamment le WAL, la conservation des données personnelles,
les fermetures et réouvertures simulées, les collectes partielles, les erreurs
de sources, les limites, les données corrompues, les sorties JSON, l'absence de
création de base et le nettoyage des temporaires après erreur ou annulation.

Preuves locales sous `data/discovery/lot31/` : `before.json`, `preservation.json`,
`flow-traders-preview.json`, `flow-traders-preview-live.json`, `test-results.xml`
et `test-results.txt`. Ces artefacts ne sont pas destinés au suivi Git.

Les sources synchronisées et la configuration opérationnelle sont inchangées.
Aucun watcher, envoi, candidature ou déploiement n'a été lancé. L'interface est
inchangée ; aucune inspection visuelle nouvelle. La validation du conteneur
Docker/VPS et la copie distante des sauvegardes restent à effectuer séparément.
