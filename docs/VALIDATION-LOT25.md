# Validation du lot 25 — Édition locale du suivi

Validation du 17 septembre 2026, Windows, Python 3.14.3.
Deux sous-agents ont livré le service transactionnel et l'interface. L'agent principal
a ajouté le serveur, les tests HTTP, la documentation et les vérifications navigateur.
Une revue croisée du serveur par l'agent du service a complété les tests de validation.

## Livraison

- Mode explicite `dashboard serve --edit-applications`, limité à `127.0.0.1`.
- Modification des six champs de suivi, avec les douze statuts existants, les limites
  de saisie et les règles de dates du modèle métier.
- Lecture récente avant édition, sauvegarde des seuls champs modifiés, historique
  avant/après et affichage des 50 derniers changements avec total.
- Révision incluant le contenu et le dernier identifiant d'historique : les modifications
  concurrentes, y compris un aller-retour de valeur réalisé par CLI, sont détectées.
- Verrou commun aux écritures, transaction SQLite atomique, aucune création de base
  ou migration. Une erreur d'historique ou de commit annule toute la modification.
- Le serveur par défaut et l'export HTML restent en lecture seule. Le mode éditable
  régénère les données lors du rechargement de page.

Voir le [guide d'utilisation](DASHBOARD-EDITING.md).

## Essais dans le navigateur

Une base synthétique séparée de huit offres a servi aux écritures :

1. Passage d'une fiche à « À candidater », ajout d'une action datée et d'une note.
2. Sauvegarde confirmée, compteur à une candidature et une offre dans la vue Candidatures.
3. Texte `<script>` affiché littéralement dans les notes et dans l'historique.
4. Brouillon modifié dans le navigateur, puis édition concurrente par le service CLI.
5. Sauvegarde refusée avec conflit, brouillon conservé, bouton Enregistrer désactivé.
6. Relecture après abandon confirmé : valeur concurrente récupérée et historique de
   deux modifications. Le conflit n'ajoute aucune modification.
7. Formulaire mobile à 390 px, sans débordement de la page ni du dialogue ; annulation
   du formulaire sans changement et absence d'erreur JavaScript.

Le serveur réel a ensuite été redémarré en mode édition avec le paquet installé.
L'ouverture du formulaire, la lecture de l'historique vide et l'annulation ont été
vérifiées. **Aucune candidature réelle n'a été modifiée.**

## Tests et préservation

- **1 459 tests réussis**, soit 97 supplémentaires ; couverture **96 %**.
- 55 tests du service : validation, verrou, conflits, WAL, transaction cohérente,
  rollback, historique borné et préservation des autres tables.
- 42 tests HTTP/CLI : accès local, jeton, origine, formats, taille, encodage, en-têtes
  ambigus, sauvegarde, conflit et erreurs sans détails privés.
- Ruff : **128 fichiers** conformes ; mypy : **55 fichiers**, sans erreur.
- Paquet installé sans mode éditable après build hors réseau depuis le lock.
  Après une dernière correction de singulier dans l'interface, paquet reconstruit
  et les 35 tests de rendu réexécutés avec succès.
- Empreintes et nombres de lignes identiques sur les **11 tables réelles**, après
  les essais, l'export HTML et la lecture du formulaire réel.
- Base réelle : **813 offres, 811 actives**, aucun changement des candidatures ou
  de leur historique. Export HTML autonome actualisé ; serveur synthétique arrêté.

Preuves locales sous `data/discovery/lot25/` : `test-results.txt`, `test-results.xml`,
`targeted-tests.txt`, `real-before.json`, `preservation.json`, `export.json` et base
`ui-demo.db`. Ces artefacts de travail sont ignorés par Git.

Aucune collecte, candidature envoyée, notification ou nouvelle automatisation.
Pas de nouvelle dépendance ni modification des références `sources/`. Le CSV
n'est pas réécrit automatiquement par une édition. L'accès multiutilisateur,
Docker et l'hébergement distant restent hors de cette validation locale.
