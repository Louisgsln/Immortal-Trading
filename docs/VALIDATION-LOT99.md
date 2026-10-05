# Lot 99 — Calendrier, conditions de candidature et couverture observée

Corrections préparées le **5 octobre 2026** à partir des défauts reproduits après
le lot 98. Ce lot ne constitue pas une vérification de l'état actuel du PC Windows
ni des catalogues employeur.

## Calendrier

Deux offres identiques commençant en janvier et en octobre 2027 obtenaient le
même score de calendrier. Les mois et trimestres explicitement associés au début
du contrat sont désormais distingués :

- janvier–avril et juin–septembre 2027 : 15 points ;
- période entièrement hors de ces fenêtres : 8 points ;
- fenêtre partiellement compatible : 11 points ;
- indications contradictoires ou date invalide : 7 points, avec explication.

Une année seule conserve la pondération existante ; elle ne fournit aucun mois.
Publication, graduation et clôture ne deviennent pas des dates de début. Aucun
jour précis n'est inventé. Les exclusions de métier, stage, Associate seul et
expérience restent prioritaires.

## Changements importants et Telegram

Une modification de début, contrat, minimum d'expérience reconnu, mention de
diplôme reconnue, visa/droit au travail ou échéance textuelle reconnue peut
déclencher une alerte. Une modification de contenu qui fait franchir le seuil
configuré peut également être signalée. Le recalcul seul reste silencieux.

Les cartes indiquent les catégories de changements et les dates reconnues dans
la description ; une deadline au jour reste sans heure inventée. Une échéance
reconnue dépassée bloque l'envoi, même sans champ structuré du connecteur.

Plusieurs modifications en attente donnent une seule alerte pour leur changement
net. Une modification annulée avant envoi est supprimée ; une nouvelle offre
encore en attente absorbe ses modifications intermédiaires. Un échec confirmé
avant livraison conserve le point de comparaison le plus ancien pour la reprise.
Les livraisons
incertaines ne sont pas retentées automatiquement. Le premier import de chaque
source reste silencieux et aucune candidature n'est envoyée.

Les extraits de visa sont des mentions de l'employeur, pas une décision sur
l'éligibilité personnelle. Négations conservées, éléments HTML masqués et
parrainages d'entreprise sans contexte de recrutement ignorés. Le dashboard
présente ces mentions et les périodes de début dans le détail.

## Couverture des filtres

Société Générale, Greenhouse filtré, Lever filtré et Workday enregistrent les
lignes examinées, retenues et rejetées, avec motif : **68 des 86 sources activées**
dans la configuration actuelle. Les autres sources ne reçoivent pas de mesures
inventées. Les recherches Workday restent partielles ; les compteurs ne prouvent
pas le rappel des métiers ciblés. Les exemples sont bornés à trente, sans titre
de poste masqué ni de formulaire générique. Filtres et budgets réseau conservés.
Les mesures sont consultables dans l'historique du dashboard après les prochaines
collectes. Les anciens passages sans mesure restent sans mesure.

Les archives de collecte sans mesure conservent leur format historique ; aucun
champ nul supplémentaire ne leur est ajouté.

Une commande compare une liste indépendante d'offres vérifiées à la base :

```console
trading-radar coverage --reference data/coverage-reference.json
```

Format JSON, avec l'identifiant stable exact du connecteur :

```json
[{"source": "societe_generale", "external_id": "26000JD4", "title": "V.I.E. One Delta Desk Analyst"}]
```

La lecture utilise un instantané SQLite en lecture seule, vérifie schéma et
intégrité, prend en compte les associations secondaires d'une même offre et
refuse références dupliquées, ambiguës ou trop volumineuses. Le taux couvre
uniquement la référence fournie. Le diagnostic de rejet porte sur le titre ;
les preuves de missions et métadonnées peuvent modifier la sélection réelle.
Aucune base absente n'est créée, aucun score n'est recalculé et aucune alerte
n'est envoyée par cette commande.

## Livraison et limites

La base de production, ses paramètres et ses journaux Windows ne sont pas
présents dans cet environnement cloud. Les domaines employeur et Telegram ne
sont pas autorisés par sa politique réseau actuelle. Aucun succès de collecte,
déploiement Windows, reprise de source bloquée ou envoi Telegram réel n'est
annoncé pour ce lot.

Les nouveaux employeurs, qualifications de rôles supplémentaires, fermetures
officielles et sauvegardes distantes nécessitent leurs preuves ou accès réels.
Ils ne sont pas déclarés résolus par ces corrections. Avant installation,
vérifier une sauvegarde de production et consulter `rescore --dry-run` sur copie.
La publication GitHub a été refusée par le contrôle automatique d'approbation :
il exige une autorisation explicite pour envoyer le correctif vers
`Louisgsln/Immortal-Trading`. Aucun commit distant, aucune tâche Windows et aucune
notification réelle n'ont été créés. Le correctif reste disponible localement.

## Validation locale

- Inventaire courant : **4 763 tests Python vérifiés**, sans cas manquant ni échec
  restant dans les rapports consolidés. La suite a été exécutée en quatre
  processus isolés, puis **244 tests des composants modifiés** ont été réexécutés
  après les derniers correctifs, tous réussis.
- Les deux incompatibilités repérées pendant les suites complètes ont été
  corrigées : ajout de `selection: null` aux anciennes archives et majuscule du
  libellé d'échéance inconnue. Les tests existants sont conservés.
- Ruff, formatage et mypy : réussis ; **99 fichiers applicatifs** vérifiés par mypy.
- JavaScript : **11 tests réussis**, syntaxe du dashboard valide.
- Chromium : calendrier, visa avec négation, compteurs et motifs de rejet
  affichés ; texte HTML importé affiché comme texte sans exécution.
- Lock vérifié ; sdist et wheel construits. Les **104 fichiers applicatifs** du
  wheel correspondent exactement aux sources. SHA-256 du wheel :
  `d83bde4eac5b676ff117ac10e2dfd84269fcd218b623ef3cd30d52201f9009d6`.
- Reprise avec le paquet construit et une base synthétique de huit offres :
  prévisualisation sans écriture, deux scans sans doublon ni envoi historique,
  sauvegarde vérifiée, restauration avec **11 tables identiques**, dashboard,
  monitoring, tendances et rétention réussis. Ce contrôle local ne vaut pas
  validation Docker ou Windows.

Les contrôles GitHub de ce correctif ne sont pas lancés, sa publication restant
bloquée. Les rapports JUnit, le paquet et les traces synthétiques restent dans
le répertoire temporaire de validation ; aucune donnée d'exploitation n'est
incluse dans le dépôt.
