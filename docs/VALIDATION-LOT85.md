# Lot 85 — Variante des missions de courtage TP ICAP

La rubrique « Responsibilities » du poste Trainee Broker, Global Broking est
maintenant reconnue comme la variante « Role Responsibilities » déjà auditée.
La qualification reste limitée à TP ICAP officiel, aux titres Trainee Broker
et à une liste unique contenant les preuves attendues de cotation et contact
client ou d'exécution. La présentation commerciale du groupe ne suffit pas.

## Aperçu des changements

Audit et collecte réelle sur copie des **991 offres** :

| Annonce TP ICAP | Avant | Après | Motif |
| --- | ---: | ---: | --- |
| [Trainee Broker, Global Broking — R5717](https://tp.wd107.myworkdayjobs.com/TP-ICAP/job/Singapore/Trainee-Broker--Global-Broking_R5717) | 0 | 66 | Missions de cotation, identification d'opportunités et relation client vérifiées ; BROKING |
| [Trainee Broker, Forward FX — R5802](https://tp.wd107.myworkdayjobs.com/TP-ICAP/job/Sydney/Trainee-Broker--Forward-FX_R5802) | 0 | 0 | Support de desk et cotations transmises aux bureaux internes ; preuves client insuffisantes |
| [Listed Execution Broker, COEX — R5715](https://tp.wd107.myworkdayjobs.com/TP-ICAP/job/New-York/Listed-Execution-Broker--COEX_R5715) | 0 | 0 | Poste expérimenté, hors règle Trainee Broker |

Les 990 autres scores restent inchangés. Aucune classe d'actifs n'est attribuée
à Global Broking à partir de la présentation générale du groupe. Les exclusions
stage, senior et Associate seul restent actives ; la règle Analyst/Associate
existante est conservée. Une rubrique répétée ou deux variantes présentes à la
fois restent ambiguës.

## Validation des lots 84–85

Deux collectes publiques réussies sur copie : 39 fiches et 69 requêtes, aucun
ajout ni clôture, une seule requalification. Aucune alerte créée ou envoyée ;
les candidatures et leurs historiques sont inchangés. Les 27 descriptions Optiver
gardent leur texte, leur score et leur date de modification.

Couverture après simulation : **454 fiches avec missions (+18), 375 avec diplôme
(+10), 296 offres pertinentes (+1), 182 prioritaires (inchangé)**.

Les tests ciblés couvrent les rubriques, bornes, conditions et contenus cachés,
la conservation du texte, les contre-exemples opérationnels et les exclusions.
Suite complète : **4 052 tests réussis, 4 ignorés**. Format et lint de 250 fichiers,
analyse statique de 90 modules réussis. Les contrôles de publication et la
vérification de l'instance active restent suivis ci-dessous après déploiement.
La session Nomura optionnelle du lot 83 reste désactivée sur cette instance tant
que sa validation manuelle et sa collecte réelle n'ont pas abouti.

Les portails des prochains employeurs ont aussi été relus ; voir l'[audit Marex,
Vitol et Trafigura](NEXT-EMPLOYERS.md). Ils ne sont pas encore surveillés.


## Installation et observation

Les deux lots sont publiés sur `main`, version applicative `cb49ae8f462f2896744feb6ddb2dff9b4acee331`,
installée le **27/09/2026 · 01:45** après sauvegarde locale vérifiée.
Les collectes du paquet installé réussissent : 27 fiches Optiver et 12 TP ICAP,
sans nouvelle annonce ni clôture, sans message de test. Les services de scan,
dashboard et Telegram ont repris ; le contrôle confirme le scanner actif.

Contrôle du **27/09/2026 · 01:47** : **991 offres,
296 pertinentes, 182 prioritaires,
454 fiches avec missions et 375 avec diplôme**.
Les 95 fichiers du paquet installé correspondent au paquet construit. Le
dashboard et son API de suivi répondent ; les 17 missions et 10 indications de
diplôme Optiver sont présentes dans les données servies au navigateur.

Vérification visuelle à 01:49 : filtre Optiver et Bachelor/Licence (10 résultats),
fiche Institutional Trader avec missions, introduction et critère d'études,
puis fiche Global Broking à 66 avec explication BROKING. Aucun avertissement ni
erreur JavaScript observé. Les filtres ont été réinitialisés après le contrôle.

Une seule variation de score confirmée : Global Broking, de 0 à 66. Les autres
scores, textes Optiver, dates de modification, candidatures et alertes antérieures
sont préservés. La surveillance conserve les 43 sources ; Nomura campus reste
en attente de sa validation manuelle.

Tous les [contrôles GitHub du code livré](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36279972194) ont réussi : Python 3.11 à 3.14,
dashboard et construction/restauration en conteneur. Les mises à jour ultérieures
de cette livraison ne concernent que le bilan et le carnet.
