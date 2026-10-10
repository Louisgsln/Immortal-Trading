# Carnet des tâches — 10 octobre 2026

Ce carnet suit l’instance OVH. Un connecteur développé ou une offre visible dans
un catalogue public ne sont pas, à eux seuls, une preuve de surveillance active.
Les validations et mesures sont dans [VALIDATION-LOTS125-127.md](VALIDATION-LOTS125-127.md).

| Priorité / tâche | État | Preuve / prochaine action |
|---|---|---|
| Publier les lots 108–124 | Fait | `53127f2` sur main ; CI 38031223402 réussie |
| Radar et Telegram H24, HTTPS privé, suivi mobile | Installé | Lots 108–124 ; vérifier à chaque déploiement |
| Mesurer découvertes, scores et alertes hebdomadaires | Développé, validation en cours | Lot 125 : lecture seule, sept jours, raisons de blocage |
| Réconcilier couverture dépôt / VPS | Validation en cours | Lot 126 : 25 → 63 sources ; profil VPS public distinct |
| Ajouter les employeurs de trading et recherche | 38 sources vérifiées deux fois | 1 486 postes de catalogue examinés ; import initial silencieux à vérifier |
| Corriger les contrats Old Mission et Point72 | Développé et testé | Valeurs publiées `Intern` et `Part Time`, autres valeurs inconnues refusées |
| Retenir la recherche Old Mission liée aux décisions de trading | Développé et testé | Missions vérifiées ; intitulé ou texte d’entreprise seuls insuffisants |
| Réconcilier les scores historiques | Aperçu réalisé | 33 fiches dérivées différentes, 11 scores avant correction ; sauvegarde/copie avant écriture |
| BNP Paribas | Bloqué par accès employeur | HTTP 403 observé le 10/10 ; garder les anciennes offres et signaler leur ancienneté |
| Optiver | Couverture partielle explicite | Une fiche Trading Automation Specialist non vérifiable ; aucune fermeture déduite |
| Workday existants | À surveiller | 503 transitoires chez Citi, Deutsche Bank et Morgan Stanley ; redirection Barclays à diagnostiquer |
| Nomura campus | En attente si CAPTCHA | Intervention humaine laissée en attente conformément au choix du propriétaire |
| Banques, courtiers et énergie non inclus au profil VPS | À faire | Relire leurs portails depuis OVH ; activer seulement après validation actuelle |
| Alertes off-cycle / stages longs 2027 | Activées | Format/année confirmés et première référence validée ; Summer hors alertes |
| Sauvegarde hors VPS | Destination à définir | Sauvegardes locales automatiques existantes ; aucune destination distante choisie |

Chaque livraison clôture ses lignes après tests, sauvegarde vérifiée, installation
et observation. Les compteurs de premier import ne doivent pas être présentés
comme un nombre garanti de nouvelles offres par semaine.
