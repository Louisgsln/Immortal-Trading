# Suivi local des candidatures

Les commandes `applications` enregistrent vos décisions dans SQLite. Elles fonctionnent sans réseau ni configuration Telegram. Elles n'envoient ni candidature ni message à un recruteur.

## Consulter et modifier

Depuis la racine du projet, utiliser `trading-radar` ou `.\.venv\Scripts\trading-radar.exe`. Remplacer `JOB_ID` par l'identifiant affiché par `list`, `applications list` ou la colonne `job_id` du CSV.

```powershell
trading-radar list --min-score 70
trading-radar applications show JOB_ID
trading-radar applications update JOB_ID --status "To Apply" --notes "Adapter le CV au desk FX"
trading-radar applications update JOB_ID --next-action "Finaliser le CV" --next-action-date "2026-09-20"
trading-radar applications list --status "To Apply"
trading-radar applications list --due-before "2026-09-20"
trading-radar applications history JOB_ID
```

Seuls les champs fournis changent. Les autres gardent leur valeur. `--due-before` inclut le jour indiqué et les actions en retard, quel que soit le statut : les prochaines actions restent vos choix explicites. Il ne compare pas les deadlines de l'employeur et ne programme pas de rappel. La liste affiche 50 fiches par défaut ; `--limit 100 --offset 100` affiche la page suivante. Tri : date d'action croissante, puis score décroissant, avec les fiches sans date d'action à la fin.

## Statuts

`New`, `Reviewing`, `To Apply`, `Applied`, `Online Assessment`, `Video Interview`, `Interview`, `Final Round`, `Offer`, `Rejected`, `Withdrawn`, `Closed`.

Toute transition explicite est permise, y compris revenir à un statut antérieur pour corriger une saisie. Chaque offre collectée commence à `New`. L'état `job_active` décrit l'observation de l'offre et reste indépendant du statut personnel : marquer une candidature `Closed` ne ferme pas l'offre à sa source ; une offre fermée ne supprime pas une candidature en cours.

Après avoir réellement candidaté ailleurs, on peut enregistrer :

```powershell
trading-radar applications update JOB_ID --status "Applied" --application-date "2026-09-19"
```

La date n'est jamais inventée lors d'un changement de statut. Elle peut rester inconnue. `application_date` et `next_action_date` acceptent uniquement `YYYY-MM-DD`, avec une vraie date calendaire ; aucune heure ni conversion UTC. Une date de prochaine action exige un libellé `next_action`.

## Champs et effacement

- `--recruiter` : texte saisi manuellement, 500 caractères maximum.
- `--notes` : 20 000 caractères maximum.
- `--next-action` : 2 000 caractères maximum.
- `--application-date`, `--next-action-date` : dates facultatives.
- `--status` : un des douze statuts ci-dessus, obligatoire dans le record mais facultatif dans chaque modification.

Pour effacer une valeur, utiliser les noms de champs avec underscores. `--clear` peut être répété ; le même champ ne peut pas être fourni et effacé ensemble.

```powershell
trading-radar applications update JOB_ID --clear notes --clear recruiter
trading-radar applications update JOB_ID --clear next_action --clear next_action_date
trading-radar applications update JOB_ID --clear application_date
```

Un texte vide ou composé d'espaces est normalisé en valeur absente. Effacer une prochaine action datée nécessite aussi d'effacer sa date. Une validation échouée ne modifie rien.

## Historique et export

Chaque modification effective conserve l'avant, l'après et un timestamp UTC dans `application_history`. Répéter exactement la même saisie ne crée pas une nouvelle entrée. Effacer une note dans la fiche courante ne l'efface pas de cet historique local. Les scans, fermetures, réouvertures et recalculs des scores ne remplacent pas les champs de suivi.

Une édition utilise le même verrou que les scans. Si un scan tourne, la commande indique que la base est occupée ; relancer après sa fin. Écriture de la fiche et historique réussissent ou échouent ensemble.

```powershell
trading-radar export --output data/jobs.csv
```

L'export comprend les champs de suivi et l'identifiant stable ; les colonnes préexistantes restent dans le même ordre, les nouvelles sont ajoutées à la fin. Les cellules commençant comme une formule sont neutralisées. Après une édition, relancer l'export pour rafraîchir le fichier ; le prochain scan l'actualise aussi. Le CSV contient les notes et contacts saisis, tout comme l'historique local ; aucun de ces fichiers n'est envoyé automatiquement.

## Démonstration et limites

`scan --demo` prépare les fiches synthétiques. Ajouter `--demo` à chaque commande `applications` pour travailler uniquement dans `data/demo.db` ; utiliser un ID issu de `applications list --demo`. `--config-dir` sélectionne une autre configuration.

Le schéma SQLite passe de 2 à 3 pour ajouter la table d'historique. Les suivis existants sont conservés ; leur passé n'est pas reconstruit. Utiliser la version actuelle du programme avec cette base.

Le suivi est disponible en ligne de commande et dans le [dashboard avec édition locale](DASHBOARD-EDITING.md), activé explicitement par `--edit-applications`. Depuis le lot 17, la [consultation des deadlines et les rappels optionnels](DEADLINES.md) respectent l'état de candidature et la date de candidature renseignée. Ils restent désactivés. Import de CSV et synchronisation externe restent à construire. Les statuts ne modifient pas les alertes générales d'offres.
