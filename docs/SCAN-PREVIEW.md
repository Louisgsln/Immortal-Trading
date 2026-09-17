# Aperçu d'une collecte avant import

`scan --dry-run` collecte les annonces et calcule les changements sur une copie
temporaire de la base. Il permet d'examiner les ajouts, modifications, recalculs,
réouvertures et fermetures que le scanner proposerait à cet instant.

```powershell
.\.venv\Scripts\python.exe -m trading_radar scan --dry-run --source flow_traders
.\.venv\Scripts\python.exe -m trading_radar scan --dry-run --company "Flow Traders"
# Démonstration synthétique hors réseau :
.\.venv\Scripts\python.exe -m trading_radar scan --dry-run --demo
```

Sans filtre, toutes les sources activées sont interrogées. Un filtre `--source`
accepte une clé configurée ou un type de connecteur. `--demo` utilise uniquement
la fixture synthétique et la base de démonstration comme référence.

## Ce qui est préservé

- Les onze tables de la base active, y compris candidatures, notes, alertes,
  historiques, dates d'observation et compteurs d'échec.
- Les exports CSV et HTML ainsi que la configuration opérationnelle.
- L'absence de base : aucun fichier ni répertoire de base active n'est créé.

L'aperçu n'initialise pas Telegram, désactive les alertes et rappels dans sa copie
de configuration et n'exporte aucun CSV. La copie vérifiée inclut les transactions
déjà validées dans le WAL SQLite. Les fichiers et verrous de simulation sont
temporaires puis supprimés. La base doit être une base SQLite sur disque, avec le
schéma actuel si elle existe ; l'aperçu ne migre pas la base d'origine.

## Lire le résultat JSON

| Champ | Signification |
| --- | --- |
| `status` | `ok`, `incomplete` si une source échoue, `error` si l'aperçu ne peut être produit |
| `read_only` | Toujours `true` : aucune modification métier de la base active |
| `generated_at` | Horodatage UTC de création de l'aperçu |
| `metrics` | Compteurs du scan simulé ; `null` en cas d'erreur globale |
| `changes` | Événements simulés, identité, titre, employeur, source, lien et score/activité avant/après |
| `ephemeral_new_ids` | Les identifiants des nouvelles offres sont propres à cette simulation |
| `error` | Erreur globale assainie ; les échecs par source figurent dans `metrics.failed` |

`changes` suit l'ordre des événements. Si une offre change plusieurs fois, son
état « avant » correspond à l'événement précédent. Pour une nouvelle offre,
`before_score` et `before_active` sont `null`. Les descriptions intégrales et
notes personnelles ne figurent pas dans le rapport. Les compteurs `relevant` et
`high_priority` reflètent la base simulée entière, pas seulement le filtre choisi.

Depuis le lot 32, chaque changement contient `changed_fields`, une liste triée
des noms de champs métier modifiés. Par exemple, `description_text` signale un
changement de description sans en exposer le texte ; `score_breakdown` peut
signaler un changement d'explication même si le score total est identique.
Les dates techniques d'observation, identifiants et payloads bruts sont exclus.
Pour une nouvelle offre, la liste est vide car aucun état antérieur n'existe.
Cette liste décrit les événements déjà produits par le scanner : elle n'ajoute
pas de nouveaux critères de création d'événements d'historique.

Codes de sortie : **0** pour un aperçu terminé, **1** pour un échec global ou une
collecte incomplète, **2** si aucune source activée ne correspond aux filtres.
Une collecte incomplète peut conserver les changements des sources réussies dans
le rapport, sans importer aucun résultat. Une erreur globale vide les changements.

## Limites et passage à l'import

Hors démonstration, l'aperçu effectue de vraies requêtes publiques : mêmes règles
robots, délais, filtres et restrictions que le scanner. Une recherche partielle
ne déduit aucune fermeture de l'absence d'une offre. L'aperçu ne rafraîchit pas les
indicateurs de santé de la base active.

Limites : 5 000 offres avant et après simulation, 10 000 nouveaux événements et
2 000 000 caractères par payload JSON lu. Un dépassement annule le rapport de
changements ; ces limites ne remplacent pas les budgets réseau des collecteurs.
La copie initiale et les vérifications SQLite lisent la base complète et exigent
de l'espace temporaire suffisant. Des fichiers auxiliaires SQLite peuvent être
gérés par SQLite lors de la lecture d'une base WAL ; la garantie porte sur les
données métier, pas sur une empreinte binaire constante de tous les fichiers.

Le résultat n'est pas un plan réutilisable d'import. Un scan ultérieur sans
`--dry-run` relit les sources et l'état actuel de la base : les annonces et les
identifiants des nouvelles offres peuvent différer. Les alertes reprennent alors
le comportement de la configuration normale. Conserver une sauvegarde vérifiée
avant une actualisation importante ; voir [BACKUPS.md](BACKUPS.md).
