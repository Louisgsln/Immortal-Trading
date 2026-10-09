# Lot 116 — Calendrier portable des échéances

La vue Échéances affiche l'heure de Paris lorsqu'une date limite contient un instant précis. Le bouton Exporter le calendrier télécharge un fichier ICS contenant les événements de la période affichée. Les prochaines actions datées et les dates limites sans heure sont des journées entières ; les dates limites précises conservent leur instant UTC.

L'export suit le même état des candidatures que l'agenda : une candidature déposée garde ses prochaines actions et perd son échéance de dépôt ; les suivis clos, retirés ou refusés ne créent pas d'événement. Les dates inconnues ou contradictoires ne deviennent pas des échéances. Chaque offre/type conserve une identité stable et les doublons internes sont exclus.

Le fichier contient les intitulés, entreprises et textes des prochaines actions, sans notes, contacts, cookies, jetons ni lien privé du Dashboard. Aucun destinataire, abonnement ou alarme automatique n'est ajouté. C'est un import ponctuel : les modifications ultérieures demandent un nouvel export et une mise à jour dans l'application de calendrier.

Vérifications : dates inclusives et fins exclusives, année bissextile, changement d'heure à Paris, conversion des décalages UTC, identités stables, exclusion des dates invalides et prévention de l'injection de propriétés ICS. Les lignes sont pliées à 75 octets UTF-8 sans casser les caractères. Chromium mobile à 390 px vérifie le téléchargement réel, les deux types d'événements, la confidentialité, la suppression de la date limite après dépôt, la sauvegarde du suivi et l'absence de défilement horizontal.

Régression finale : 284 tests Python du Dashboard, 4 tests de déploiement des stages et 28 tests JavaScript passent. Ruff, mypy du nouveau lecteur de couverture et vérification des différences passent. Publication séparée après sauvegarde vérifiée, avec conservation des identités, historiques, base et curseur Telegram.
