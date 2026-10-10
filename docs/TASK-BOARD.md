# Carnet des tâches — 10 octobre 2026

Ce carnet suit l’instance OVH. Un connecteur développé ou une offre visible dans
un catalogue public ne sont pas, à eux seuls, une preuve de surveillance active.
Les validations et mesures sont dans [VALIDATION-LOTS125-127.md](VALIDATION-LOTS125-127.md),
[AUDIT-EMPLOYERS-20261010.md](AUDIT-EMPLOYERS-20261010.md),
[VALIDATION-LOT128.md](VALIDATION-LOT128.md) et
[VALIDATION-LOTS129-131.md](VALIDATION-LOTS129-131.md). Ce carnet a été réconcilié avec le VPS :
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
| Workday existants | Reprise observée, à surveiller | Citi, Deutsche Bank, Morgan Stanley et Barclays frais au contrôle final ; garder les erreurs de pagination/503 explicites si elles reviennent |
| Intitulés quantitatifs rejetés chez Jump et Flow Traders | À qualifier sur missions | Jump 8027898 off-cycle 2027 ; Flow PhD Graduate Quantitative Researcher : annonce complète et contre-exemples avant élargissement |
| Recherche Point72 collectée mais non qualifiée | À auditer | Cubist Quantitative Researcher et variantes : score nul sans preuve de missions retenue ; ne pas attribuer des points au seul intitulé |
| Nomura campus | En attente si CAPTCHA | Intervention humaine laissée en attente conformément au choix du propriétaire |
| Nomura professionnels | Pagination récente à surveiller | Import interrompu sur pages incohérentes ; reprise selon la cadence normale, accès campus distinct |
| Bank of America campus / off-cycle — lot 129 | Installé et observé | Premier succès OVH, 10 fiches ; Milan 15033 à 96/100 et référence bancaire 7/7 |
| Banques comparables — lots 129–130 | Installé et observé | Bank of America (deux portails), Jefferies, RBC, ING, Wells Fargo et Santander ; 70 sources / 62 employeurs |
| Autres banques, courtiers et énergie non inclus au profil VPS | À faire | Lots suivants : relire les portails depuis OVH et valider avant activation |
| Alertes off-cycle / stages longs 2027 | Activées et vérifiées | 38 fiches satisfont les critères au contrôle ; année/formats conservés ; premiers imports silencieux |
| Réponse du Dashboard avec davantage de sources | Installé et vérifié | CPU 1 du lot 128 conservé ; HTTPS 12.549 s avec 70 sources ; regroupement des lectures prévu au lot 135 |
| Regrouper les lectures de conflits et lacunes | À mesurer | Profilage du lot 128 : lectures par source encore coûteuses ; conserver toutes les preuves de santé |
| Sauvegarde hors VPS | Destination à définir | Sauvegardes locales automatiques existantes ; aucune destination distante choisie |

Chaque livraison clôture ses lignes après tests, sauvegarde vérifiée, installation
et observation. Les compteurs de premier import ne doivent pas être présentés
comme un nombre garanti de nouvelles offres par semaine.

## Lots bancaires demandés le 10 octobre

| Lot | Travail et résultat attendu | Validation avant clôture | État |
|---|---|---|---|
| 129 — Bank of America campus | Collecteur distinct des professionnels et événements ; témoin Global Markets Sales and Trading 2027 Off-Cycle Analyst – Milan | Catalogue entier paginé, identités et fiches employeur concordantes ; score expliqué ; Summer et événements exclus des alertes | Installé et observé ; Milan 96/100 |
| 130 — Autres banques | Jefferies campus, RBC, ING, Wells Fargo et Santander vérifiés ; JPMorgan campus reste HTTP 403 | Deux lectures cohérentes par source ; offres off-cycle/longues documentées ; contrats et année conservés sans inférence | Installé et observé ; sept ajouts réussis |
| 131 — Suivi de couverture | [Carnet par portail](BANK-CAMPUS-COVERAGE.md) et [sept témoins](BANK-CAMPUS-REFERENCE.json) ; conversions CDI séparées du stage, mois alternatifs conservés | Tests de régression, premier import sans envoi, ancienne base/historique/curseur préservés, premiers succès en production | Livré ; témoins 7/7, données préservées |

### Prochains lots ouverts

Les numéros ci-dessous réservent les prochaines livraisons ; ils ne constituent
pas une preuve de développement ou d'installation. Chaque lot doit présenter un
avant/après et les limites restantes avant clôture.

| Lot / priorité | Travail concret | Critère de clôture | État / dépendance |
|---|---|---|---|
| 132 / haute — campus complémentaires | Relire Barclays, Citi et Deutsche Bank ; distinguer professionnels, programmes, événements et offres ouvertes ; contrôler les campagnes européennes | URL officielle et pagination prouvées, témoin externe retrouvé, source installée et première réussite OVH ; conserver les portails refusant l'accès dans la liste des blocages | À faire ; après 129–131 |
| 133 / haute — missions quantitatives | Auditer Jump 8027898, Flow PhD Graduate Quantitative Researcher, Cubist/Point72, Bank of America 14722 et Jefferies 1954 | Responsabilités employeur positives et contre-exemples ; score expliqué sans points tirés de la présentation générale ; aperçu historique, sauvegarde puis réconciliation silencieuse | À faire ; fiches déjà repérées |
| 134 / haute — stages et dates | Auditer les formats/années inconnus ING et Santander ; rendre durée, mois alternatifs, graduation et langues exploitables dans les filtres existants | Valeur et extrait employeur concordants ; inconnu reste inconnu ; Summer et mauvais millésime restent hors alertes ; contrôle Dashboard et tests sur fiches réelles | À faire ; sources 130 |
| 135 / moyenne — architecture Dashboard | Mesurer les lectures de conflits/lacunes par source puis les regrouper ; comparer la réponse mobile avant/après sur la même base | Temps et nombre de lectures consignés ; santé, preuves de lacunes, statuts, notes et révisions identiques ; contrat du Dashboard et HTTPS privé vérifiés | À mesurer ; performance 128 conservée |
| 136 / moyenne — couverture dans le temps | Comparer découvertes, programmes éligibles, causes de rejet et alertes réellement envoyées sur sept jours ; enrichir la référence de témoins indépendants | Rapport daté par portail ; imports initiaux séparés des nouveautés ; absence d'un témoin devenue tâche explicite, aucune fausse promesse de débit hebdomadaire | À faire après une semaine d'observation |
| 137 / moyenne — sauvegarde distante | Choisir une destination puis définir rétention et restauration sur copie isolée | Destination autorisée, archive vérifiée et restauration testée ; base, historiques et état Telegram conservés | En attente de destination ; sauvegardes locales actives |

### Incidents et contrôles récurrents

| Tâche | Action / preuve attendue | État |
|---|---|---|
| BNP, JPMorgan campus et NatWest | Reprendre selon les accès publics disponibles ; conserver HTTP 403 explicite et anciennes fiches, sans contournement | Ouvert |
| Nomura campus | Laisser l'intervention humaine en attente ; ne pas confondre avec le portail professionnels | En attente, décision du propriétaire |
| Workday et Nomura professionnels | Suivre dernier succès, erreur et reprise de pagination ; un résultat nul n'est valide qu'après un catalogue cohérent | Surveillance |
| RBC `markets` | Contrôler le volume par requête (482/500 lors de l'audit) ; étudier une partition publique si le plafond est atteint | Surveillance, import tronqué interdit |
| Déploiements | Sauvegarde vérifiée, import silencieux sur copie, alertes et suivi préservés, curseur Telegram non réinitialisé, mêmes liens privés | À chaque livraison |

Pour chaque nouveau portail, consigner : URL officielle, accès observé, périmètre,
pagination, identifiant employeur, offre témoin, date du dernier contrôle et preuve
du premier succès OVH. Une erreur d'accès reste une tâche ouverte et ne vaut pas
absence d'offres. Les étapes de livraison sont : développé → testé → installé →
observé ; seule la dernière permet de marquer une source comme surveillée.
