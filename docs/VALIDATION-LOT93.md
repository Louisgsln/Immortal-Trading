# Lot 93 — Fiabilité des cinq sources signalées

Ce lot traite les erreurs UBS Professionnels, Optiver, BNP Paribas, Citi et BP
observées le 28 septembre. Les 71 sources restent activées. Il ne change ni
les scores, ni le suivi des candidatures, ni le seuil des alertes.

## Causes et corrections

- **UBS** : les ex æquo du tri par date déplaçaient des annonces entre pages.
  Le tri alphabétique seul reproduit aussi un doublon. Le collecteur utilise
  désormais le formulaire public `MatchedJobs`, son jeton anonyme et les sept
  mots-clés correspondant exactement au filtre de titres existant. Chaque
  recherche est paginée, triée alphabétiquement et relue ; les annonces communes
  à plusieurs recherches doivent être identiques. Une incohérence relance
  l'ensemble une seule fois. Aucun jeton de session n'est conservé.
- **Optiver** : une même annonce était publiée en dernière position d'une page
  puis en première position de la suivante. L'API plafonne les pages à 16.
  Le parcours chevauche maintenant une position : doublons strictement identiques
  seulement, compte unique égal au total officiel, liens uniques et relecture
  initiale. Une annonce perdue ou modifiée provoque toujours un échec.
  Deux parcours publics ont retrouvé les **166 identifiants uniques**.
- **BNP** : deux pages portant la même référence présentaient des dates,
  descriptions et contrats différents. Toutes deux étaient intitulées
  « Stage - Assistant Trader ». Les intitulés explicitement stage/internship
  sont écartés avant import, conformément au ciblage demandé. Les **25 fiches
  retenues** ne présentent plus ce conflit. Les contradictions sur les offres
  admissibles restent en quarantaine. Le portail de recrutement renvoyant 403,
  aucune version n'a été choisie arbitrairement ; aucune restriction contournée.
- **Citi** : une référence Workday sans titre peut être recoupée avec la
  recherche officielle et sa fiche, uniquement si les identités, le titre
  visible, les métadonnées et le lien de candidature concordent. La référence
  `26985835` désigne un poste AVP hors cible. Pour `26997063`, la recherche CXS
  exacte confirme une seule annonce dans « Operations - Transaction Services » ;
  cette catégorie précise et son identifiant officiel sont hors du périmètre
  front office. Une catégorie inconnue, un résultat absent ou un compte incohérent
  ne permettent pas de supprimer une lacune. Aucun titre n'est inventé.
- **BP** : les lignes ne contenant que `RQ` et six chiffres sont reconnues
  et comptées, avec au maximum dix références incomplètes par collecte.
  Elles ne bloquent plus les autres fiches. Une fiche publique BP n'autorise
  l'exclusion d'une référence que si son employeur et son lien de candidature
  identifient exactement cette référence et si son titre est hors cible.
  La référence `RQ111627`, observée comme un poste d'opérations maritimes,
  renvoie ensuite 404 sur le portail public : la lacune reste signalée si elle
  n'est pas vérifiable au moment de la collecte. Une disparition ne vaut pas
  confirmation de fermeture.

Les recherches demeurent partielles : **aucune fermeture par absence**.
Les pages manquantes ou bloquées ne sont jamais transformées en résultats vides
valides. Les reprises restent dans les budgets de temps et les intervalles
par site ; les filtres Analyst / Associate et les exclusions de séniorité
restent inchangés. Les anciens stages stockés ne sont ni effacés ni déclarés fermés.

## Validation

Deux scans réels successifs sur copie : **133 offres**, **308 requêtes par passage**,
cinq collecteurs terminés, aucun ajout, aucune modification, fermeture ou alerte. UBS retrouve
31 fiches, Optiver 27, BNP 25, Citi 48 et BP 2 ; seule la référence BP ci-dessus
reste incomplète. Les **1 160 offres existantes** conservent leurs scores et
leur qualification ; candidatures et historiques d'alertes sont préservés.

Pendant ce travail, le scanner a signalé le même défaut chez **Morgan Stanley** :
`JR037398` sans titre ni lien. La forme `JR` suivie de six chiffres est aussi
reconnue, avec les mêmes limites et sans référence codée en dur. Ses **20 fiches
valides** sont récupérées ; cette référence reste signalée et aucune absence
ne ferme une offre.

Suite locale complète : **4 481 tests Python réussis, 4 ignorés**. Les deux
nouveaux cas BP/Morgan Stanley, ajoutés ensuite, passent aussi dans les 74 tests
ciblés de récupération. **11 tests JavaScript**, Ruff sur **263 fichiers** et
mypy sur **95 modules** réussis. Les preuves d'installation et de CI sont
consignées ci-dessous.


## Installation vérifiée

Commit applicatif `6b310e47f445cb6820ba570238dc02442b8b0773`, poussé sur `main` et installé le
**28/09/2026 · 09:41**, après sauvegarde vérifiée. Les **100 fichiers
applicatifs** correspondent au paquet construit. Le fichier privé, les paramètres
locaux et le lanceur de session sont inchangés ; les trois services déjà actifs
ont été redémarrés, sans message Telegram de test.

Le paquet installé collecte **153 offres sur six sources**.
Aucun ajout, modification, fermeture ou alerte de test ; les anciens scores,
candidatures et historiques sont conservés. Dashboard et API du suivi accessibles,
scanner repris. La page Santé des sources a été rechargée et vérifiée dans le
navigateur, avec les lacunes explicitement affichées et les heures locales.

Au contrôle **28/09/2026 · 10:00** : **69/71 sources à jour**.
Sources encore à examiner : Citi (refus temporaire d'accès), BP (fiche manquante).
**57 sources**, dont UBS, Optiver et BNP,
ont été recollectées automatiquement après la vérification d'installation.
Morgan Stanley est revenue à jour au passage suivant. Citi a réussi les deux
scans sur copie et la collecte installée, puis son portail a renvoyé un nouveau
**HTTP 403 à 09:57**. Les offres restent conservées ; ce refus d'accès distinct
du défaut de fiches déclenche la temporisation normale, sans contournement.
Le radar n'est donc pas présenté comme intégralement sain.

Les [six contrôles GitHub du commit applicatif](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36392933793) ont réussi :
Python 3.11 à 3.14 (**4 483 tests réussis, 4 ignorés**), les **11 tests JavaScript**
et le contrôle de l'image avec restauration isolée.
