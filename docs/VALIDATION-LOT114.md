# Lot 114 — Couverture observable des stages

La vue Santé des sources distingue la référence des stages de la fraîcheur de collecte. Elle affiche, pour les seules sources actives, la validation datée du périmètre de recherche, les références en attente, les incidents courants et le nombre de stages actifs conservés en base. Les incidents sont présentés en premier dans des cartes adaptées au téléphone.

La référence provient uniquement d'une observation réussie du journal, portant le marqueur booléen de validation depuis la date de déploiement. Une collecte partielle, contradictoire, échouée ou future ne devient pas une référence. Un échec ultérieur ne supprime pas une référence déjà acquise ; son incident reste visible séparément. La validation ne signifie pas que tous les postes d'un employeur sont couverts.

La lecture ne crée ni base, ni migration, ni collecte, ni message. Un historique illisible ou dépassant les limites de lecture s'affiche comme indisponible. Une configuration explicitement prévalidée sans date ne reçoit pas une date inventée.

Vérification : tests de lecture seule, validation stricte des marqueurs, périodes, états partiels, sources désactivées, absence de fichier et journal incomplet ; régressions du Dashboard et de la santé. Déploiement séparé avec sauvegarde vérifiée et contrôle des identités, historiques et curseur Telegram.
