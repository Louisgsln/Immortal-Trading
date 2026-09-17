# Lot 28 — Plan de conservation et exercice de récupération

Travaux du **17 septembre 2026**. Trois sous-agents ont réalisé le moteur de
conservation, sa commande et sa documentation, puis un audit indépendant des
qualifications. L'agent principal a intégré les changements, complété l'exercice
de reprise et vérifié les données réelles.

## Fonction livrée

`backup plan DIRECTORY` vérifie les archives ZIP directement présentes dans un
dossier, puis indique les fichiers conservés et ceux hors de la politique choisie.
La sortie existe en texte ou avec `--json`. La conservation combine les dernières
sauvegardes et un exemplaire par jour UTC ou semaine ISO dans les fenêtres choisies.

Chaque archive est vérifiée intégralement : structure ZIP, manifeste, empreinte,
schéma SQLite, intégrité et relations. L'inventaire est borné à 100 archives,
512 Mio par fichier et 2 Gio au total. Les changements pendant la lecture et les
chemins liés sont refusés. Une archive invalide bloque tous les candidats au retrait.

La commande ne supprime ni ne déplace rien. Elle n'ouvre pas la configuration ou
le `Repository`, ne crée aucune sauvegarde et ne lance aucun transport de notification.
La politique proposée n'est pas activée sous forme de purge ou de tâche planifiée.
Contrat, exemples et limites dans [BACKUP-RETENTION.md](BACKUP-RETENTION.md).

## Exercice réel

1. Empreintes et nombres de lignes des onze tables de la base active conservés
   dans `data/discovery/lot28/before.json`.
2. Sauvegarde créée et vérifiée : `data/backups/radar-lot28-2026-09-17.zip`.
   Snapshot SQLite de **21 155 840 octets**, archive de **21 156 553 octets**.
3. Restauration vers le nouveau fichier `data/restore-check/lot28/jobs.db`.
   Les **11 tables** correspondent exactement à la base active et à l'état initial.
   Contrôles d'intégrité et relations valides ; base active non remplacée.
4. Audit réel du dossier `data/backups` : **2 archives valides**, total
   **42 071 442 octets**, toutes deux conservées avec les paramètres par défaut.
   Aucun candidat et aucune suppression. La première archive reste celle du lot 19.

La base conserve **813 offres, 811 actives et 45 scans métier**. Les candidatures,
historiques, scores, observations des sources et alertes restent inchangés. Aucun
scan réseau, envoi de candidature, notification ou watcher n'a été lancé.

Les preuves `recovery.json` et `backup-plan.json` sont sous
`data/discovery/lot28/`. Les sauvegardes locales ne constituent pas une copie
distante et ne protègent pas contre la perte de ce disque.
Après l'audit, `preservation.json` confirme les empreintes inchangées des onze
tables et des deux archives.

## Intégration et contrôles

Les tests couvrent les règles combinées et les frontières de dates UTC/ISO,
les égalités de dates, les fichiers corrompus, budgets, chemins liés, dates futures,
modifications pendant lecture, sorties CLI et absence d'écriture.

Deux scénarios d'intégration utilisent de vraies archives : un candidat reste
restaurable avec son historique de candidature et son alerte incertaine ; une
archive invalide bloque toute recommandation sans modifier les fichiers.

L'exercice `scripts/smoke_container.py` inclut désormais `backup plan`. Le contrôle
local teste le paquet installé avec des données synthétiques et restaure les onze
tables. Il ne valide ni Docker, ni Linux, ni les permissions d'un volume distant.

- **1 664 tests réussis**, soit **55 nouveaux** ; couverture Python **96 %**.
- Ruff : **139 fichiers** conformes ; mypy : **59 fichiers**, sans erreur.
- Paquet reconstruit hors réseau depuis `uv.lock`, testé sans installation éditable.
  Les deux modules livrés correspondent exactement aux fichiers installés.
- Preuves : `data/discovery/lot28/test-results.xml` et `test-results.txt`.
- Aucune dépendance, migration ou modification des sources synchronisées.

## Audit des qualifications

L'[audit indépendant](QUALIFICATION-AUDIT-LOT28.md) examine les 813 descriptions,
dont 188 avec un minimum d'expérience extrait. Neuf cas sont documentés avec
extraits, offsets, identifiants et empreintes.

Un futur correctif local est justifié pour `Experience Desirable:` directement
attaché au nombre d'années dans une annonce Crédit Agricole CIB. Aucun faux minimum
dû à une alternative diplôme/expérience n'a été confirmé ; des minima indépendants
doivent rester applicables. Un cas Susquehanna d'expérience additionnelle non
extraite nécessite une analyse distincte. Aucune règle de score n'a été modifiée
dans ce lot.

## Limites restantes

Le build Docker et la reprise sur l'hôte cible restent à exécuter ; l'absence de
runtime a été constatée au lot 27. La copie distante, la surveillance prolongée
et une éventuelle application contrôlée de la rétention restent hors de ce lot.
L'interface du dashboard n'a pas changé et n'a pas fait l'objet d'une nouvelle
inspection visuelle.
