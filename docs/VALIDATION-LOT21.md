# Validation du lot 21 — Santé historisée, cache Workday et couverture Jump

17 septembre 2026, Windows / Python 3.14.3. Trois sous-agents ont pris en charge l'historisation, le cache HTTP et l'audit des sources. L'agent principal a intégré le watcher, corrigé la sélection Jump, étendu l'exercice de reprise et exécuté la suite finale sur l'installation verrouillée.

## Historique des contrôles de santé

Commandes `monitor record/history/show`, sans réseau ni modification de la base métier. Les rapports sont écrits dans `data/health-history` avec identifiant unique, format versionné et SHA-256. Publication atomique sans écrasement, limites de taille, validation des lectures et protection des chemins SQLite et fichiers associés.

Les états critiques sont archivés avant le retour du code 1. La consultation propose pagination et filtres ; la comparaison porte sur les deux dernières observations et distingue changements de sources et régressions. Si la base est indisponible, les sources ne sont pas faussement déclarées retirées. Un changement du seuil de fraîcheur est signalé.

Deux observations réelles ont été enregistrées et relues par les commandes CLI : **healthy**, **24 sources fraîches**, aucune régression. Les empreintes et nombres de lignes des **11 tables** sont identiques avant et après ; les **811 offres**, leurs candidatures et historiques sont préservés.

Preuves : `data/discovery/lot21/monitoring-history.json`, `monitoring-preservation.json` et les deux rapports sous `data/health-history`. Ces archives sont séparées du snapshot SQLite et ne sont pas incluses dans `backup create`. Aucune planification n'est installée. Guide : [MONITORING.md](MONITORING.md).

## Cache conditionnel Workday

L'option propre à Workday `conditional_details: true` active la revalidation des détails par ETag/Last-Modified lorsqu'un cache est injecté. Le watcher partage ce cache mémoire entre scans, tout en créant un nouveau client HTTP à chaque passage afin de relire les règles robots. La configuration livrée laisse cette option désactivée.

Une réponse 304 réutilise uniquement un corps encore présent, non expiré et associé à des métadonnées compatibles. Les refus, erreurs et réponses inutilisables ne servent jamais de contenu périmé. Autorisation, cookies, `Vary`, `no-store` et réponses privées empêchent le stockage. La cadence et les compteurs de requêtes continuent de s'appliquer.

Limites par défaut : **256 entrées**, **1 Mio par corps**, **16 Mio au total**, **une heure depuis le dernier 200**. Les 304 ne prolongent pas la résidence. Aucun cache disque ni nouvelle table ; un redémarrage vide le cache. Les recherches et inventaires partiels Workday ne changent pas.

Les tests utilisent des transports simulés. Aucun portail réel n'a été interrogé pour mesurer ses validateurs : **aucun gain de bande passante en production n'est revendiqué**. Ce mécanisme réduit les octets lorsque le serveur répond 304, pas le nombre de requêtes. Guide : [WORKDAY-CACHE.md](WORKDAY-CACHE.md).

## Audit des accès et correction Jump

Citadel Securities et JPMorgan ont été vérifiés avec les URL publiques déjà configurées : **HTTP 403 dès robots.txt**, une requête par source. Le contrôle s'arrête avant les pages cibles ; aucun autre endpoint ni moyen de contournement essayé. Les deux sources restent désactivées. Les preuves réseau sont dans `data/discovery/lot21/coverage/access-probe.json`.

Le corpus complet Jump du lot 12 contient **108 annonces**. La nouvelle règle reconnaît deux familles de rôles, avec département vérifié et preuves propres aux missions : développement logiciel avec les traders ; développement quantitatif des plateformes de l'équipe de trading avec cycle de développement complet. Les présentations génériques, compétences seules et support de production seul ne suffisent pas.

| ID Jump | Effet sur le corpus audité | Score après correction |
| --- | --- | --- |
| 8104832 — Python Software Engineer | Nouvellement sélectionnée ; missions avec les traders et minimum publié de deux ans | 51 |
| 7822791 — Quantitative Developer | Nouvellement sélectionnée ; développement pour l'équipe de trading | 53 |
| 6190021 — Quantitative Developer / Trading Team | Déjà sélectionnée, exclusion technique corrigée par preuve du rôle | 53 |

La sélection Jump passe de **23 à 25**. Ces trois rôles ne deviennent ni juniors ni prioritaires : **aucun nouveau score ≥55 ou ≥70**, aucune date d'entrée inventée. Les contre-exemples d'outils transverses, infrastructure, stages et expérience senior restent exclus de cette extension. XTX reste à une annonce sélectionnée sur dix, score 65 pour le contrôle positif.

Les règles de score générales n'ont pas été élargies à tous les développeurs. La reconnaissance est volontairement bornée aux formulations auditées. D'autres rôles mixtes et le libellé d'expérience `5+ year track record` restent à examiner séparément.

Il s'agit d'une analyse du **catalogue sauvegardé**, pas d'une confirmation de disponibilité actuelle des postes. Aucune offre historique n'a été injectée dans SQLite, aucun rescore de la base réelle exécuté. La correction sera appliquée lors d'une prochaine collecte Jump. Diagnostic et contre-exemples : [COVERAGE-AUDIT-LOT21.md](COVERAGE-AUDIT-LOT21.md). La baseline et le résultat corrigé sont conservés séparément dans `data/discovery/lot21/coverage/`.

## Vérification finale

- **1 067 tests réussis**, soit **113 supplémentaires**, couverture globale **96 %**.
- **48 tests** d'historisation : états critiques, filtres, dates, empreintes et JSON corrompus, limites, chemins protégés, collisions et comparaisons. Module couvert à **94 %**, CLI à **100 %**.
- **49 nouveaux tests** du cache et de son usage Workday : validateurs, remplacement, erreurs, confidentialité, TTL pendant une requête, éviction et isolation. Module cache couvert à **100 %**.
- **2 tests d'intégration du watcher** : même cache entre passages, clients fermés et recréés, robots redemandés avant revalidation. Boucle simulée bornée, aucun watcher réel démarré.
- **14 tests Jump** : preuves positives et contre-exemples, titres seniors, stage et expérience minimale. Revue indépendante des résultats du corpus par le sous-agent d'audit.
- Exercice de reprise existant enrichi : `monitor record/history/show` sur la base synthétique, alerte inconnue conservée, comparaison des onze tables après archivage de santé et restauration.
- Ruff valide sur **109 fichiers** ; mypy valide sur **46 modules**. Dépendances du lock inchangées.
- Paquet reconstruit hors réseau depuis `uv.lock`, installé de manière non éditable sous `data/validation-lot20-venv`, puis suite complète exécutée contre cette installation.

## Limites et suite

Aucun fichier synchronisé `sources/` modifié, aucune notification ou candidature envoyée. Seules les deux requêtes d'accès explicitement décrites ont été effectuées ; aucun inventaire réel complet ni watcher lancé.

La validation Docker/VPS du lot 20 reste à exécuter sur un hôte équipé. Ce lot ne prétend pas lever cette limite. Les prochaines étapes applicatives sont l'actualisation de Jump, la mesure réelle des validateurs Workday et un dashboard en lecture seule exploitant offres, candidatures et rapports de santé. Les copies distantes et la conservation des archives restent à organiser séparément.
