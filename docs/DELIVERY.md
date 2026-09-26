# Livraison continue des lots

Préférence du propriétaire confirmée le 25 septembre 2026 : poursuivre la roadmap,
publier chaque lot validé sur `main` et installer la version sur l'instance active.
Une PR en brouillon n'est plus la destination finale par défaut.

Cible confirmée le 25 septembre 2026 : exclure des priorités et alertes les postes
uniquement **Associate**. Conserver les intitulés explicitement ouverts aux deux
niveaux **Analyst / Associate**, sous réserve des autres critères habituels.
Cette préférence de ciblage n'attribue aucun nombre d'années à un grade.

Priorités confirmées le 26 septembre 2026 : fiabilité des sources, fiches plus
complètes, ciblage, couverture des recherches, puis les autres chantiers
d'exploitation et de suivi. L'enrichissement IA et la comparaison avec un CV
sont retirés du périmètre. Leur place revient à une extension importante du
nombre d'employeurs de finance, trading, market making et activités de marchés.
Le [plan de développement](DEVELOPMENT-PLAN.md) précise les livrables attendus.

1. Choisir un périmètre borné dans la roadmap et vérifier l'état du dépôt distant.
2. Développer dans la copie de travail, indépendante du scanner en exploitation.
3. Vérifier le code, les tests pertinents et les parcours utilisateur modifiés.
   Toute modification de données est d'abord mesurée sur une sauvegarde restaurée.
4. Publier sur `main` sans réécriture d'historique. En cas de changement distant,
   intégrer et revérifier avant publication. Respecter les protections de branche.
5. Construire le paquet, vérifier une sauvegarde, conserver le paquet précédent,
   puis mettre à jour l'instance avec un arrêt bref des services concernés.
6. Confirmer le redémarrage, l'activité réelle du scanner, le dashboard et les
   contrôles GitHub. Consigner le résultat et la prochaine priorité dans la roadmap.

Les fichiers `.env`, bases SQLite, notes personnelles, captures et sauvegardes
d'exploitation restent locaux. Un envoi distant de sauvegarde demande une
destination choisie ; cette préférence de livraison n'en définit aucune.
La fusion et le déploiement d'un lot n'activent ni candidature automatique,
ni nouvelle dépense ou infrastructure externe.

Ce document fixe le mode de livraison. Il ne crée pas de tâche planifiée de
développement ; seules les tâches d'exploitation installées assurent la collecte
continue, le dashboard, Telegram et la sauvegarde quotidienne.
