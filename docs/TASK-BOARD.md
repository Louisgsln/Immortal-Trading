# Carnet des tâches — 10 octobre 2026

Ce carnet suit l’instance OVH. Un connecteur développé ou une offre visible dans
un catalogue public ne sont pas, à eux seuls, une preuve de surveillance active.
Les validations et mesures sont dans [VALIDATION-LOTS125-127.md](VALIDATION-LOTS125-127.md),
[AUDIT-EMPLOYERS-20261010.md](AUDIT-EMPLOYERS-20261010.md) et
[VALIDATION-LOT128.md](VALIDATION-LOT128.md). Ce carnet a été réconcilié avec le VPS :
les anciennes mentions Windows et exclusions globales des stages étaient historiques.

| Priorité / tâche | État | Preuve / prochaine action |
|---|---|---|
| Publier les lots 108–124 | Fait | `53127f2` sur main ; CI 38031223402 réussie |
| Radar et Telegram H24, HTTPS privé, suivi mobile | Installé | Lots 108–124 ; vérifier à chaque déploiement |
| Mesurer découvertes, scores et alertes hebdomadaires | Installé et vérifié | Lot 125 : sept jours, raisons de blocage ; découvertes distinctes des alertes envoyées |
| Réconcilier couverture dépôt / VPS | Installé | Lot 126 : 25 → 63 sources ; profil VPS public distinct |
| Ajouter les employeurs de trading et recherche | Installé et vérifié | 38 sources vérifiées deux fois et initialisées ; 307 fiches / 78 au seuil / 69 à examiner, import sans alerte |
| Corriger les contrats Old Mission et Point72 | Installé et testé | Valeurs publiées `Intern` et `Part Time`, autres valeurs inconnues refusées |
| Retenir la recherche Old Mission liée aux décisions de trading | Installé et testé | Missions vérifiées ; intitulé ou texte d’entreprise seuls insuffisants |
| Réconcilier les scores historiques | Corrigé | 33 champs dérivés réconciliés, 11 scores ; sauvegarde vérifiée, zéro alerte créée |
| BNP Paribas | Bloqué par accès employeur | HTTP 403 observé le 10/10 ; garder les anciennes offres et signaler leur ancienneté |
| Optiver | Couverture partielle explicite | Une fiche Trading Automation Specialist non vérifiable ; aucune fermeture déduite |
| Workday existants | À surveiller | 503 transitoires chez Citi, Deutsche Bank et Morgan Stanley ; redirection Barclays à diagnostiquer |
| Intitulés quantitatifs rejetés chez Jump et Flow Traders | À qualifier sur missions | Jump 8027898 off-cycle 2027 ; Flow PhD Graduate Quantitative Researcher : annonce complète et contre-exemples avant élargissement |
| Recherche Point72 collectée mais non qualifiée | À auditer | Cubist Quantitative Researcher et variantes : score nul sans preuve de missions retenue ; ne pas attribuer des points au seul intitulé |
| Nomura campus | En attente si CAPTCHA | Intervention humaine laissée en attente conformément au choix du propriétaire |
| Nomura professionnels | Pagination récente à surveiller | Import interrompu sur pages incohérentes ; reprise selon la cadence normale, accès campus distinct |
| Banques, courtiers et énergie non inclus au profil VPS | À faire | Relire leurs portails depuis OVH ; activer seulement après validation actuelle |
| Alertes off-cycle / stages longs 2027 | Activées et vérifiées | 31 fiches satisfont les critères ; 61/63 références validées ; exclusions générales de stages retirées à la collecte pour 23 sources |
| Réponse du Dashboard avec davantage de sources | Installé et vérifié | Lot 128 : 274 tests ciblés ; HTTPS 7,748 s lors du contrôle ; CPU Dashboard limité à 1 |
| Regrouper les lectures de conflits et lacunes | À mesurer | Profilage du lot 128 : lectures par source encore coûteuses ; conserver toutes les preuves de santé |
| Sauvegarde hors VPS | Destination à définir | Sauvegardes locales automatiques existantes ; aucune destination distante choisie |

Chaque livraison clôture ses lignes après tests, sauvegarde vérifiée, installation
et observation. Les compteurs de premier import ne doivent pas être présentés
comme un nombre garanti de nouvelles offres par semaine.
