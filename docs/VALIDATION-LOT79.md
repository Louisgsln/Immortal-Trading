# Lot 79 — Historique de fiabilité par source

Chaque collecte terminée conserve désormais sa source, son résultat et sa durée.
Le dashboard présente les essais attribués des dernières 24 heures, leur taux de
réussite, leur durée moyenne et les cinq derniers passages. Les fiches incomplètes
et les références en conflit ne comptent pas comme une réussite complète.

Les anciens cycles globaux ne permettent pas de retrouver les sources réussies :
ils sont exclus et l'interface signale la constitution progressive de l'historique.
La lecture est bornée, sans écriture ni migration ; une erreur ou un dépassement
rend les statistiques indisponibles, sans inventer un taux à partir d'un extrait.
Les causes publiques sont normalisées ; les erreurs brutes restent privées.
Ce suivi ne modifie ni la cadence, ni les reprises, ni les avis Telegram.

Validation locale : 124 tests réussis, un test ignoré ; 11 tests JavaScript
réussis ; analyse statique de 88 modules. Contrôles des fenêtres temporelles,
des données invalides, des limites, de l'absence de création de base et de
l'enregistrement réel du scanner. Déploiement et contrôles distants à confirmer.
