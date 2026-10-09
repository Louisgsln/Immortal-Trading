# Lot 118 — Références internships fiables

Les catalogues publics complets Greenhouse filtrés et SIG déclarent désormais une référence de périmètre validée après leurs contrôles de total, identités et pagination. `complete=False` est conservé : une absence dans le périmètre filtré ne ferme aucune offre. Aucune référence n’est injectée manuellement. La première collecte validée reste silencieuse pour les stages ; seules les détections ou modifications suivantes peuvent devenir alertables.

Le radar et le Dashboard partagent le même lecteur du journal : marqueur JSON booléen exact, succès, dates avec fuseau comprises entre le déploiement du périmètre et l’observation. Les échecs ultérieurs ne suppriment pas la preuve. Les anciens enregistrements malformés sont ignorés sans fabriquer de référence. La limite de 10 000 scans a été supprimée au profit de preuves positives parcourues en flux, sans chargement complet du journal en mémoire. Aucun changement de schéma, de politique stages, de base ou de curseur Telegram.

Validation locale : 271 tests Python de couverture, rollout silencieux/dédoublonnage, scanner, politique, Greenhouse, SIG, Optiver et Morgan Stanley campus réussis. Ruff et mypy des nouveaux lecteurs réussis. Les tests comprennent un journal de plus de 10 000 scans, des dates avec décalage horaire, des marqueurs invalides et la conservation des alertes historiques.

Déploiement : sauvegarde vérifiée et contrôle de conservation avant/après, image immuable dédiée, cinq services contrôlés et HTTPS privé vérifié. Les sources ne sont déclarées prêtes qu’après une vraie collecte réussie sous cette version.
