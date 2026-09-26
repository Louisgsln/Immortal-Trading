# Lot 76 — Catalogue HSBC professionnels changeant

## Incident et comportement

Le 26 septembre 2026 à 20:37:16 Paris, le scanner reçoit des pages HSBC
professionnels dont les totaux diffèrent : `HSBC professional total changed
during pagination`. Il conserve les offres existantes et n'importe pas de
résultat partiel. Le même type d'incident figurait dans le journal à 08:04.

L'adaptateur utilise désormais la reprise déjà éprouvée pour UBS et Optiver.
Un total qui change, une page répétée entre deux pages valides, ou une première
page différente à la relecture provoquent une seule nouvelle lecture de toute
la liste. Toutes les recherches sont recommencées : aucune annonce de la
tentative abandonnée ne reste dans la collection. Les fiches ne sont demandées
qu'après validation de la liste stable.

Les deux lectures partagent le délai maximal initial et l'espacement des
requêtes. Le compteur inclut la tentative abandonnée. Un second changement
reste un échec, puis le scanner applique sa temporisation habituelle. Les
erreurs d'identité, formats invalides, fiches incohérentes, restrictions 403/429
et conflits entre recherches ne déclenchent pas cette reprise. Aucune fermeture
n'est inférée d'une absence et aucune règle de score n'est modifiée.

## Vérifications

Onze scénarios supplémentaires couvrent la récupération des trois incidents,
la suppression des résultats des recherches antérieures, l'absence de reprise
sur refus/format/identité/fiche, et le partage du délai maximal. Les tests
existants vérifient aussi l'échec sur une instabilité persistante. Les 57 tests
HSBC professionnels réussissent.

Lecture publique réelle avec l'adaptateur modifié : trois offres retenues,
20 requêtes, catalogue cohérent. Aucun message Telegram de test ni écriture
dans la base active pendant cette vérification. Cette lecture stable valide
la compatibilité du portail ; la récupération d'une instabilité est vérifiée
par les tests contrôlés et n'est pas artificiellement provoquée sur le site.

Suite complète Windows : **3 919 tests réussis, quatre ignorés**. Mypy, Ruff et
formatage réussis.

## Installation et reprise

Publié sur `main` : `5827fff2de89ac88b015f23e2198460d21030c61`, installé le
26 septembre 2026 à 20:47:42 Paris après la sauvegarde vérifiée
`scheduled-20260926T184734322448Z.zip`. Les 90 fichiers applicatifs et ressources
installés correspondent au paquet construit. Scanner, Telegram et dashboard actifs.

HSBC professionnels réussit à 20:48:23 : trois offres, aucun ajout ni changement.
Au contrôle de 20:49:05, **40 sources sur 40 sont à jour** et la supervision du
processus est saine. Nomura campus et Macquarie ont également repris. Ces succès
ne garantissent pas la disponibilité permanente des portails ; le CAPTCHA Nomura
peut réapparaître et les contrôles restent en place.

Dashboard et API de suivi répondent. Les 973 offres, leurs scores, candidatures,
historiques et alertes sont préservés. Le total reste de 282 pertinentes et 175
prioritaires, avec 295 fiches de missions, 329 mentions de diplôme et 523 dates
de publication connues. Aucun message Telegram de test ni rejeu d'alerte.

Observation prolongée à 20:50:26 : UBS professionnels répète un identifiant entre
pages, après une reprise complète à 20:50:16. La seconde incohérence reste un
échec explicite ; aucune ligne partielle n'est importée. L'état passe à
**39 sources à jour sur 40**, avec une nouvelle tentative UBS après dix minutes.
Cette variation confirme la nécessité d'afficher l'heure du contrôle et de
conserver les validations de pagination.

Python 3.11–3.14, dashboard Node et construction/restauration isolée du conteneur
ont réussi en [CI](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36263771213).
