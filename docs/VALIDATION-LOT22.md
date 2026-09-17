# Validation du lot 22 — Dashboard local en lecture seule

17 septembre 2026, Windows / Python 3.14.3. Trois sous-agents ont livré l'accès aux
données, l'interface et les tests de rendu avec documentation. L'agent principal a
intégré l'export, le serveur, le CLI et l'exercice de reprise, puis vérifié le navigateur.

## Fonctions livrées

- `dashboard export DESTINATION` produit un HTML autonome avec styles, interactions et données embarqués. Aucune dépendance Python ajoutée, aucun CDN requis.
- `dashboard serve` fournit un instantané en mémoire sur `127.0.0.1:8765`. Relancer la commande pour actualiser son contenu.
- Vues Offres, Candidatures et Santé des sources ; recherche, filtres, tri, pagination de 25 lignes et détail des scores, descriptions, échéances et notes.
- Interface française, navigation au clavier, détail sous forme de dialogue, mise en page adaptée aux petits écrans. Les descriptions et explications issues des sources conservent leur langue d'origine.

Guide : [DASHBOARD.md](DASHBOARD.md). Le dashboard permet de consulter le suivi ; les
modifications restent accessibles par les commandes `applications` existantes.

## Données et conservation

Export réel : **811 offres**, **809 actives**, **163 actives avec score ≥70**. Les
**24 sources activées sont fraîches** au moment de la génération, avec deux rapports
de santé antérieurs consultables. Aucun suivi n'a encore quitté le statut `New`.

Les offres et candidatures sont lues dans une transaction SQLite en lecture seule,
sans initialisation du dépôt ni migration. La santé et l'historique sont des
observations séparées. Une base absente, incompatible ou incohérente empêche l'export ;
une archive de santé indisponible produit un avertissement sans masquer les offres.
La limite de 5 000 offres provoque une erreur explicite, sans troncature silencieuse.

Les nombres de lignes et empreintes de contenu des **11 tables**, ainsi que les
empreintes des deux archives de santé, sont identiques avant et après l'export.
Preuve locale : `data/discovery/lot22/dashboard-preservation.json`. Le fichier livré
est `data/dashboard/index.html` ; il contient les notes du suivi et doit rester privé.

## Vérifications

- **1 170 tests réussis**, dont **103 nouveaux**, couverture Python globale **96 %**.
- Accès aux données : **52 tests**, incluant WAL, lecture concurrente, erreurs de schéma, données incohérentes, limites et URL invalides.
- Rendu et export : **35 tests**, incluant contenu HTML hostile, JSON non fini, politique de sécurité, fichiers protégés, non-écrasement et nettoyage après erreur.
- Serveur et CLI : **16 tests**, incluant accès local, refus des chemins privés et méthodes d'écriture, en-têtes de sécurité, arrêt et port occupé.
- Exercice synthétique de reprise enrichi avec l'export du dashboard : huit offres, fichier présent, base préservée. Il s'exécute aussi dans le scénario Docker préparé.
- Ruff valide sur **115 fichiers** ; mypy valide sur **49 modules**.
- Paquet reconstruit hors réseau depuis `uv.lock`, installé sans mode éditable, puis testé. Les trois fichiers d'interface sont bien embarqués et l'export réel provient de cette installation.

La vérification navigateur a porté sur les données réelles : recherche « Paris »
(15 offres), filtre score ≥70 (3 offres), ouverture du détail, retour par Échap,
vue des candidatures vide, 24 sources fraîches et deux rapports de santé. Le rendu
à 390 pixels a révélé un élément de tableau dépassant de la page ; son conteneur a
été corrigé. Après correction, largeur de page et largeur disponible sont identiques
(375 pixels hors barre de défilement), et la date de l'instantané reste visible.

Le test du bouton Réinitialiser a également révélé un conflit entre l'identifiant
du bouton et la méthode native du formulaire. L'appel utilise désormais explicitement
la méthode du prototype ; la vue Candidatures conserve les offres inactives lors de
la réinitialisation. Après correction, une recherche sans résultat puis Réinitialiser
revient aux 809 offres actives ; Suivant affiche les lignes 26–50, page 2 sur 33.
La réinitialisation des candidatures conserve bien l'option Toutes les offres.
Les 106 tests ciblés du dashboard et de la reprise ont été relancés sur le paquet
reconstruit après les derniers ajustements d'interface.

## Limites

Le HTML et le serveur présentent un instantané, sans mise à jour automatique. Les
filtres ne modifient aucune donnée. Aucun watcher, collecte réelle, envoi Telegram
ou formulaire de candidature n'a été lancé ; aucun fichier `sources/` modifié.

La couverture de 96 % concerne Python ; les interactions JavaScript ont été vérifiées
dans le navigateur et leur syntaxe contrôlée avec Node. La validation Docker/VPS
reste à réaliser sur un hôte équipé, comme documenté au lot 20. Ce lot livre un
dashboard local, sans hébergement distant.
