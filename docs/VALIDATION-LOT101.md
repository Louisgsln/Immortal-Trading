# Lot 101 — Import du suivi avec aperçu et historique

Livraison du 6 octobre 2026. Le suivi peut maintenant recevoir un fichier JSON
révisé. La commande affiche les changements par défaut, sans écrire dans la base :

```console
trading-radar applications import tracking.json
```

```json
{"format_version": 1, "applications": [
  {"job_id": "identifiant-exact-du-radar", "status": "Applied", "application_date": "2026-10-06"}
]}
```

Chaque ligne fournit l'identifiant exact d'une fiche existante et les seuls champs
à modifier. Champs omis conservés ; valeur `null` explicite pour effacer un champ
facultatif. Les statuts et dates sont validés par les règles habituelles. Aucun
rapprochement par titre, aucune date d'envoi inventée, aucune candidature envoyée.

L'application exige le token de l'aperçu et une nouvelle sauvegarde locale :

```console
trading-radar applications import tracking.json --apply --expect TOKEN --backup data/backups/import-101.zip
```

Le token lie le fichier et l'état courant des suivis concernés. Un changement
depuis l'aperçu impose une nouvelle lecture. L'ensemble des lignes est validé
avant écriture, sous le verrou commun des écrivains. La sauvegarde est créée et
vérifiée avant l'import. Modifications et historique sont enregistrés dans une
seule transaction ; un échec annule tout le lot. Une répétition sans changement
ne crée ni nouvel historique ni sauvegarde superflue.

Base existante au schéma courant exigée ; aucune création ou migration par
l'import. Les identifiants et clés JSON dupliqués, champs étrangers, fichiers
supérieurs à 2 Mo et lots de plus de 1 000 lignes sont refusés. Les erreurs CLI
ne recopient pas les valeurs privées importées.

Validation : 174 tests Python réussis sur import, suivi, dashboard, décisions
d'alerte et stockage. Tests de sauvegarde, rollback après le premier changement,
aperçu périmé, concurrence, absence de base et erreurs privées inclus. Ruff,
formatage et mypy réussis. Les exercices utilisent seulement des données
synthétiques ; aucun suivi de production n'est importé.
