# Lot 98 — Offre Société Générale One Delta manquée

Le signalement porte sur [V.I.E. One Delta Desk Analyst, 26000JD4](https://careers.societegenerale.com/en/job-offers/vie-one-delta-desk-analyst-26000JD4-en),
à New York, publiée le 28 septembre 2026. L'offre figure dans l'annuaire anglais
officiel, mais était absente de la base au moment du diagnostic.

## Cause confirmée

La source réussissait ses collectes avec 34 fiches. Son filtre de titres
Trading/Markets ne retenait ni « One Delta » ni « Desk Analyst » : la fiche
n'était donc jamais lue. Le score simulé sur sa description complète était
également de zéro, faute de catégorie de métier reconnue dans le titre.
Un état de source « à jour » confirme le bon déroulement de la collecte définie ;
il ne prouve pas que son ciblage couvre toutes les offres pertinentes.

## Correction

- Le filtre Société Générale inclut `one delta`, `delta one` et `desk analyst`.
  Les exclusions et limites de collecte restent actives ; une recherche partielle
  n'entraîne aucune fermeture par absence.
- Pour ce type de titre, le collecteur vérifie une unique liste de missions dans
  la rubrique employeur des responsabilités : programmation des outils de desk,
  pricing, backtesting et analyse du risque/P&L. Les formulations vérifiées sont
  comparées à des puces complètes : une négation, un élément manquant ou caché,
  une rubrique de profil ou une présentation de l'entreprise ne suffisent pas.
- Ces preuves permettent la catégorie `TRADING_TECH`, y compris pour un titre
  Analyst. Le contrôle du métier, de l'employeur et de la source évite d'étendre
  cette exception à tout titre portant un simple indicateur technique.
- La limite explicite du VIE, qui n'est pas autorisé à trader lui-même, est
  conservée. La pondération métier vaut **22/30**, pas celle d'un trader exécutant.
  Les règles d'exclusion des stages, des grades et des expériences restent prioritaires.

Le score calculé de l'offre est **90/100** : métier 22, junior 20, calendrier 15,
front office 15, produits 10 et mots-clés 8. Il s'agit d'une priorité de lecture,
pas d'une probabilité de recrutement. L'en-tête donne le 1er février 2027 comme
date de début ; le texte conserve aussi une formulation de disponibilité dès
que possible et un délai indicatif de trois mois. Ces informations restent
visibles sans fabriquer d'échéance de candidature.

La classification dépend de preuves dans la fiche, et non de la référence
26000JD4 codée en dur. Les autres titres nouvellement retenus peuvent rester
non classés si leurs missions ne sont pas encore vérifiées. La couverture n'est
pas annoncée comme exhaustive pour tous les VIE ou tous les postes quantitatifs.

## Validation et livraison

**289 tests ciblés réussis**, puis **36 tests du nouveau fichier** avec les
contre-exemples supplémentaires : import depuis l'annuaire, titre alternatif,
missions manquantes, niées ou cachées, mauvais employeur/source, exclusions
et unicité de l'alerte après deux collectes. Ruff, le formatage et mypy passent.
La suite complète et les preuves de collecte et d'installation sont consignées
ci-dessous.

Deux collectes publiques sur une copie de la base ont réussi : **35 fiches**, avec
**une nouvelle offre au premier passage**, puis **zéro ajout et zéro modification**
au second. Le premier passage consomme 38 requêtes (contrôle d'accès compris),
le second 37. L'offre 26000JD4 atteint 90 ; une seule alerte normale est mise en
file sur la copie, sans aucun envoi réseau. Les **1 196 anciens scores**, les
suivis et les alertes existantes sont préservés. Aucune fiche n'est fermée.

## Installation et résultat réel

Le code `12f70ae` est publié sur `main` et installé le **28 septembre à 18:34**,
après sauvegarde vérifiée. Les **100 fichiers applicatifs** installés correspondent
au paquet construit ; les paramètres locaux et les secrets sont préservés.
Le scanner, le dashboard et Telegram ont repris leur activité.

Le cycle autonome Société Générale se termine à **18:40:40** : **35 fiches,
1 nouvelle, 0 modifiée, 0 fermée, aucun conflit ni fiche manquante**. Il délivre
**une seule alerte Telegram** pour l'offre signalée. La base confirme son score
de 90 et l'état envoyé de cette alerte. Les 34 anciennes fiches Société Générale
conservent leurs scores et leurs catégories.

Le deuxième cycle autonome, terminé à **18:49:13**, retrouve les mêmes
35 fiches : **0 ajout, 0 modification, 0 fermeture et 0 nouvelle alerte**.

La fiche est vérifiée dans le navigateur à **18:42** : une seule ligne en
recherchant « One Delta », New York, score 90, publication au 28 septembre,
description complète, conditions de diplôme et explication du classement.
Le passage dans le dashboard n'envoie aucune candidature et ne modifie pas le suivi.

La suite locale complète termine avec **4 702 tests réussis et 4 ignorés**.
Les 36 cas nouveaux y sont inclus. Les [six contrôles GitHub](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36451741028)
du code applicatif `12f70ae` sont réussis : Python 3.11 à 3.14, dashboard
JavaScript, puis construction et vérification du conteneur isolé.
