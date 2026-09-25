# Lot 53 — Associate exclu de la cible junior

## Problème et décision

L'alerte HSBC **Associate, Securities Lending Trader** (`563774612276577`)
obtenait 80/100, dont 8/20 de compatibilité junior : Associate était un bonus
partiel et non une exclusion. La description indique une expérience préalable
sans minimum numérique reconnu. Le grade ne permet pas d'inventer une durée.

Le propriétaire a demandé de ne plus retenir les postes uniquement Associate,
et confirmé de conserver les offres ouvertes aux Analyst. La nouvelle règle
annule le bonus junior et ajoute un motif explicite d'exclusion : **Poste
Associate sans ouverture explicite au niveau Analyst**. Le score total est nul.
Les fiches restent consultables et les candidatures restent conservées.

Les alternatives Analyst/Associate, Associate/Analyst, `or`, `and`, `&` et `|`
entre les deux grades sont reconnues dans le titre, y compris les entités HTML.
La présence isolée d'Analyst ailleurs, un indice campus ou une description junior
ne suffisent pas. Les exclusions stage, VP ou expérience minimale continuent
de s'appliquer aux titres mixtes. Cette règle décrit la cible du propriétaire,
pas une équivalence universelle entre les grades des employeurs.

## Impact répété sur sauvegarde restaurée

Sauvegarde cohérente créée, vérifiée et restaurée sur une copie de **783 offres**.
Seuls les champs de score et de niveau changent sur **52 fiches Associate** :
20 scores passent à zéro, dont **15 auparavant prioritaires**. Les 32 autres
avaient déjà un score nul et reçoivent le motif supplémentaire. HSBC passe de
**80 à 0**, avec compatibilité junior **8 à 0**.

Les **731 autres fiches**, notamment Analyst/Associate, restent identiques.
Huit tables inchangées : schéma, observations source, entreprises, scans,
alertes, historique d'alertes, candidatures et historique de candidatures.
Dates de collecte et exigences numériques conservées. Deuxième application sans
effet ; aucune collecte simulée et aucun message envoyé par le recalcul.

## Vérifications

Les tests couvrent les titres HSBC et autres Associate, les indices junior
contradictoires, les alternatives Analyst dans les deux sens, les frontières de
mots, l'expérience et les grades supérieurs. Un parcours complet de collecte
vérifie qu'Associate n'est pas mis en file, tandis qu'Analyst/Associate reste alerté.
La reprise d'une alerte ancienne en attente la supprime de la file d'envoi après
recalcul. Les rappels respectent aussi l'exclusion, même avec un seuil réglé à zéro.
Les messages déjà reçus ne sont ni supprimés ni réécrits.

Suite complète Windows initiale : **3 048 tests réussis, quatre ignorés**. Après
les garde-fous sur le seuil zéro et les variantes de titre : 160 tests ciblés
réussis, puis 38 tests Associate sur la version finale. Ruff, formatage et mypy
vérifiés.

## Livraison du 25 septembre 2026

Le commit `e388d8954f2fea711a6e2e6271f3bbe7728ec1d3` est publié sur `main`.
Installation après sauvegarde vérifiée à 22:53 Paris, puis recalcul transactionnel
sur l'instance active : mêmes 52 fiches, 20 scores changés et 15 anciennes priorités.
Les huit tables protégées sont identiques ; répétition sans effet.

Le dashboard et l'API des candidatures répondent HTTP 200. HSBC affiche 0/100 et
le motif Associate ; 13 titres mixtes restent présents, dont des offres toujours
prioritaires. Les 783 offres et le suivi sont conservés. Scanner, dashboard et
Telegram sont actifs ; collectes HSBC professionnels, Nomura et Macquarie réussies
après redémarrage. La collecte HSBC suivante est sans nouvelle modification,
confirmant la concordance avec le recalcul hors ligne.


La [validation GitHub du code installé](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36188416369)
est réussie sur Python 3.11, 3.12, 3.13 et 3.14, ainsi que pour la construction
Docker et la restauration synthétique. Rapport Python 3.12 : **3 059 tests réussis**,
couverture **96 %**.
