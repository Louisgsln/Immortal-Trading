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

Suite complète Windows : **3 919 tests réussis, quatre ignorés**. Mypy, Ruff et formatage réussis. Observation après installation à compléter.
