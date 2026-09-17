# Validation du lot 17 — Deadlines et rappels

17 septembre 2026, heure de Paris, Windows / Python 3.14.3. Suite du [suivi des candidatures](VALIDATION-LOT16.md).

## Livré

- `deadlines list` : consultation des échéances, horizon et score filtrables, dates passées facultatives et preuves affichées.
- `deadlines reminders` : simulation locale de l'éligibilité, sans file d'attente ni initialisation de Telegram.
- Extraction prudente des dates explicites dans les descriptions conservées, combinée aux deadlines structurées déjà validées.
- Rappels J−7/J−3/J−1 intégrés au scanner et au watcher existants, derrière un réglage distinct **désactivé par défaut**.
- Déduplication, revalidation avant envoi, maintien du bootstrap silencieux, suppression selon l'état de candidature et la fraîcheur.

Guide : [DEADLINES.md](DEADLINES.md). Aucune tâche planifiée, aucun watcher ni envoi réel lancé dans ce lot.

## Mesures sur les données locales

Analyse des **811 fiches conservées**, sans accès réseau ni nouvelle observation des portails :

| Résultat | Nombre |
| --- | ---: |
| Timestamps de deadline déjà stockés, tous HSBC campus | 7 |
| Instants supplémentaires reconnus dans les descriptions | 6 |
| Total des échéances précises consultables | 13 |
| Dates complètes, mais sans heure/fuseau fiable | 5 |
| Fiches sans échéance exploitable reconnue | 793 |
| Contradictions détectées dans ce corpus | 0 |
| Rappels actuellement éligibles au seuil de score 70 | 0 |

La liste par défaut présente 17 fiches : elle exclut une ancienne date BNP du 28 décembre 2025. Les six nouveaux instants concernent quatre fiches Nomura campus, une Citi et une Optiver. Les cinq dates seules concernent trois fiches BNP, une Crédit Agricole CIB et une Nomura campus.

L'absence de rappel éligible se décompose ainsi : trois échéances précises hors de la fenêtre de sept jours, dix fiches sous le seuil de score et cinq dates sans instant fiable. Les 793 échéances inconnues sont omises des plans détaillés et ne génèrent rien. Ces chiffres ne représentent pas 18 opportunités adaptées au profil : les stages et programmes de découverte restent exclus par le classement.

Exemples tirés des descriptions déjà conservées :

- [Nomura Graduate Internship, Singapour](https://nomuracampus.tal.net/candidate/so/pm/1/pl/1/opp/1487-2027-Global-Markets-Graduate-Internship-Program-Singapore/en-GB) : 30 septembre 2026 à 23:55 SGT, soit **15:55 UTC**. Le stage conserve un score nul.
- [Citi Capital Markets Summer Analyst, Hong Kong](https://citi.wd5.myworkdayjobs.com/2/job/Hong-Kong--Hong-Kong/Banking---Capital-Markets--Summer-Analyst--Hong-Kong---APAC--2027_26984751) : 30 octobre 2026 à 23:59 HKT, soit **15:59 UTC**. Ce n'est pas une date déduite de l'année du programme.
- [Optiver Career Kickstarter](https://www.optiver.com/join-us/jobs/institutional-sales-and-trading/amsterdam/career-kickstarter-trading-2026) : candidatures avant 17:00 CEST le 20 septembre 2026, soit **15:00 UTC**. La deadline ultérieure des assessments n'est pas confondue avec celle de candidature. Ce programme de découverte conserve son score nul.
- Crédit Agricole CIB : la date du 31 octobre 2026 reste une **date sans heure**. Citi publie ailleurs « 30 October, 23:59 HKT » sans année : cette autre fiche reste inconnue malgré un titre de programme 2027.

## Contrat de précision

Le parseur reconnaît un ensemble restreint de formulations anglaises, avec année obligatoire. Il conserve les extraits de preuve. Les jours de semaine, heures, offsets et dates sont validés ; des dates ou fuseaux contradictoires empêchent le rappel. UTC, GMT, HKT, SGT, CET, CEST et offsets numériques explicites sont acceptés ; aucun fuseau n'est déduit du pays et aucune année du titre de poste.

Les dates sans heure et les zones non prises en charge restent imprécises. La normalisation et les adaptateurs optionnels n'attribuent plus UTC à une deadline dépourvue de fuseau. Les contrats existants des portails restent inchangés : `validThrough` technique, `endDate` Workday ou date de début ne deviennent pas automatiquement une échéance candidat.

Les preuves textuelles sont calculées à la lecture, sans réécrire les faits collectés. SQLite et le CSV conservent leurs sept deadlines structurées ; `deadlines` expose les preuves supplémentaires. Aucun score, timestamp d'observation ou historique de candidature n'a été modifié. Les descriptions n'ont pas été revérifiées en réseau pendant ce lot.

## Comportement des rappels

Les fenêtres sont `(3 j, 7 j]`, `(1 j, 3 j]` et `(0, 1 j]`, comparées à l'instant UTC exact. Un passage ne prépare que la fenêtre actuelle. Le message précise cette notion de fenêtre ; après une interruption, le programme ne rattrape pas trois rappels simultanés.

Éligibilité : offre active, score suffisant, observation datant d'au plus 24 h par défaut, statut New/Reviewing/To Apply et absence de date de candidature. Les étapes Applied, Online Assessment, Video Interview, Interview, Final Round, Offer, Rejected, Withdrawn et Closed bloquent le rappel.

La clé de file d'attente associe offre, fenêtre et deadline UTC. Le moteur relit tout avant envoi et supprime les rappels devenus obsolètes. Une deadline modifiée reçoit une nouvelle clé. Les états sent/unknown/sending/suppressed ne sont pas rejoués pour la même clé ; les erreurs de rejet explicite restent retentables tant que le rappel est pertinent. Une issue réseau incertaine n'est pas traitée comme un échec certainement non livré.

Il faut simultanément activer les alertes générales, configurer Telegram et activer `deadline_reminders_enabled`. Le réglage reste **false**, `ALERTS_ENABLED` reste **false**, et Telegram reste non configuré. La première collecte silencieuse de chaque source et le mode démo restent sans rappel. Les statuts ne modifient pas les notifications générales d'offres nouvelles/modifiées.

## Vérification

- **796 tests réussis**, soit **85 nouveaux**, couverture globale **95 %** ; parseur et CLI d'échéances **100 %**, planification **94 %**, scanner **96 %**.
- Ruff valide sur **89 fichiers** ; mypy valide sur **37 modules**.
- Formats réels, heures 12/24 h, fuseaux, offsets, date sans année, date sans heure, ambiguïtés, invalidité et contradictions testés.
- Bornes exactes des trois fenêtres, douze statuts, date de candidature malgré retour au statut New, fraîcheur limite et timestamps futurs testés.
- Double activation, bootstrap silencieux, idempotence, deadline modifiée/supprimée, offre fermée, score réduit et changement de statut entre mise en file et livraison testés.
- Simulation d'envois acceptés, rejetés, inconnus et d'un arrêt après marquage sending. Aucun appel Telegram réel.
- Consultation CLI avec alertes générales activées mais sans token ; absence d'écriture métier, isolation démo et filtre d'expiration à l'heure exacte vérifiés. Le filtre de score de consultation ne réduit pas le seuil d'éligibilité aux rappels.

La base reste à **811 fiches**, dont **809 actives**, **163 scores ≥ 70** et **247 scores ≥ 55**. Les 811 suivis restent New, l'historique de candidature reste vide et la table d'alertes reste vide. Pas de migration SQLite ni de dépendance supplémentaire. Rapports locaux dans `data/discovery/lot17/`, ignorés par Git.

## Limites et suite logique

La reconnaissance de texte n'est pas exhaustive : formats localisés, mois abrégés, dates sans année et deadlines à plusieurs tours restent à traiter avec des preuves dédiées. Les jours seuls ne déclenchent pas d'envoi. Une offre peut fermer avant sa deadline annoncée ; la vérification de fraîcheur réduit ce risque sans garantir l'ouverture.

Prochaine étape : **gestion opérateur des alertes au résultat incertain**, avec consultation de la file, décisions explicites et historique, puis sauvegardes/restauration SQLite et validation d'exploitation. L'envoi Telegram réel et la surveillance prolongée restent à valider séparément.
