# Lot 124 — Contrat du Dashboard et livraison cohérente

La commande `python -m trading_radar.dashboard_contract` contrôle les ressources réellement installées dans l’image : modules JavaScript, contrôles référencés, identifiants uniques et empreintes des scripts/styles de la politique de sécurité. Le validateur accepte aussi la politique HTTP pour détecter un en-tête devenu incohérent avec la page. Il ne publie que des compteurs et des états, sans données de candidature ni valeur d’accès.

Ce contrôle est exécuté sans réseau ni données métier dans l’image candidate, avant la mise en service, et ajouté à la CI après construction. Le Dashboard HTTPS livré subit ensuite le même contrôle. Les tests rejettent les contrôles manquants, identifiants dupliqués, ressources altérées ou externes, offres dupliquées/incohérentes et politique HTTP périmée.

Les fichiers Python des livraisons précédentes sont normalisés avec Ruff, sans changement de comportement. L’appel HTML du récapitulatif est explicite pour satisfaire le contrôle de types. Le dépôt distant étant encore au lot 107, les améliorations publiques déjà déployées sont également synchronisées, sans fichiers d’environnement, bases, sauvegardes, liens privés ni captures.

Livraison groupée des lots 122–124 sur une image immuable, construite à partir du contexte validé du lot 121. Sauvegarde vérifiée avant activation ; vérification de la base, des identifiants, historiques, alertes déjà envoyées, curseur et préférences Telegram. Le rollback concerne le code et les images, sans restauration automatique de la base métier. Les résultats mesurés figurent dans `DELIVERY-LOTS122-124.json`.
