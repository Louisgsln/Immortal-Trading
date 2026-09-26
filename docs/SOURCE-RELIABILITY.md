# Collectes indépendantes et cohérence des sources

Le watcher planifie chaque source séparément, dans la limite de `concurrency`.
Les sources les plus en retard passent en premier. Une collecte terminée libère
son créneau ; elle peut livrer ses alertes et se reprogrammer sans attendre un
cycle global. L'intervalle est compté depuis la fin de la dernière tentative.
La durée de lecture et l'attente d'un créneau s'ajoutent à cet intervalle.

Chaque tentative emploie sa propre session HTTP anonyme et relit les politiques
d'accès public. L'espacement des requêtes reste partagé par site entre toutes
les sources, y compris UBS campus et professionnels. La séparation des cookies
ne permet donc pas de multiplier les requêtes vers un même site.

`source_timeout` borne toute collecte à 600 secondes par défaut. Les limites
plus strictes d'un collecteur continuent de s'appliquer. Après un échec,
l'attente augmente, y compris avant le premier succès : deux fois l'intervalle,
puis quatre, huit et au maximum une heure, sans raccourcir un intervalle configuré
supérieur à une heure. Un succès rétablit l'intervalle normal.

UBS, Optiver et HSBC professionnels vérifient la pagination et relisent sa première page avant de
demander les fiches. Si des pages cohérentes séparément changent entre elles,
une seule reprise de toute la liste est permise dans le budget initial. Les
lignes de la tentative abandonnée ne sont ni mélangées ni importées. Une
deuxième incohérence laisse la source en échec. Une restriction d'accès,
un CAPTCHA ou une page structurellement invalide ne déclenche pas cette reprise.
Chez HSBC, la reprise recommence également les recherches précédentes de la
même tentative, pour ne pas mélanger des réponses de deux instantanés. Les
conflits entre recherches, les limites et les fiches invalides restent des
échecs explicites. Le compteur de requêtes inclut la tentative abandonnée.

Depuis le lot 82, UBS compare les lignes de la première page par identifiant,
avec l'intégralité de leur contenu. Le tri par date peut permuter des offres
identiques : cette seule permutation ne signifie plus que le catalogue a changé.
Un identifiant remplacé, un contenu modifié, un doublon ou un total différent
reste rejeté. Les doublons et liens invalides sont aussi contrôlés à la relecture.

Le verrou `.scan.lock` réserve les collectes à un seul processus. Le verrou
historique `.lock` protège les écritures et la livraison des notifications,
sans rester détenu pendant les lectures des sites employeurs. Les modifications
du suivi peuvent ainsi fonctionner pendant une collecte ; les transactions
SQLite continuent de sérialiser les écritures.

Chaque tentative produit ses propres métriques et son identifiant de source
dans le journal. En mode watch, un « scan » enregistré correspond donc désormais
à une source, alors que les anciens enregistrements pouvaient regrouper plusieurs
sources. Les comptes historiques de scans ne sont pas directement comparables
avant et après cette évolution ; les nouvelles offres et candidatures gardent
leurs historiques. Le signal d'activité suit la tentative active la plus ancienne.

Les alertes en attente d'une source en échec restent différées jusqu'à une
collecte réussie. Une collecte ciblée n'envoie pas les alertes des autres sources.
Les livraisons incertaines ne sont jamais répétées automatiquement.
# Causes et calendrier visibles depuis le lot 74

Dans Santé des sources, chaque ligne indique l'intervalle configuré et la
première heure possible de la prochaine collecte. Après échec, le délai est
calculé avec la même règle que le scanner. Une heure passée signifie que la
source peut être prise en charge, sans affirmer qu'elle a déjà été collectée :
le scanner doit être actif et disposer d'une place. L'état est daté du chargement.

Les causes d'échec sont présentées par catégories courtes. Les messages bruts,
URLs de transport et paramètres ne sont pas exposés. `/status` reprend les causes
et les reprises possibles. La reconnaissance de la page d'erreur Macquarie
n'autorise aucune redirection et ne garantit pas une réparation du portail.

## Historique attribué depuis le lot 79

Dans la colonne de dernière réussite, déplier le taux pour consulter la durée
moyenne et les cinq derniers passages sur 24 heures. Chaque résultat inclut
désormais sa source et son heure de fin en base. Les anciens succès globaux
ne sont pas attribués par déduction ; l'interface signale cet historique incomplet.
Une liste partielle volontairement ciblée peut être collectée avec succès ; ce
taux ne mesure pas la couverture de tout le catalogue employeur. Les références
en conflit et les fiches manquantes comptent comme essais non pleinement réussis.
Une lecture invalide ou dépassant 10 000 cycles dans la fenêtre n'affiche aucun
taux partiel. Cette vue ne change pas le calendrier ni les notifications Telegram.
