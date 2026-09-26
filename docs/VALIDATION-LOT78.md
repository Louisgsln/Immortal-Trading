# Lot 78 — Horaires sans suffixe de fuseau

Correction demandée le 26 septembre : ne plus afficher la mention de ville ou
de décalage après les horaires. Les messages et le dashboard affichent par
exemple `26/09/2026 · 22:04`. La conversion Europe/Paris, les changements
saisonniers et les journées calendaires du lot précédent restent actifs.

Les libellés des graphiques, du détail d'offre, de l'aide Telegram et du
récapitulatif sont allégés. Les CSV contiennent la date et l'heure locales sans
suffixe de décalage. Les dates saisies sans heure restent inchangées. Les
instants stockés en base et les métadonnées des rapports techniques conservent
leur précision ; aucune migration ou modification du suivi n'est effectuée.

Vérification locale : **264 tests réussis, un ignoré**, onze tests JavaScript,
Ruff et Mypy réussis. Les tests existants continuent de couvrir minuit, été/hiver,
les changements saisonniers et l'indépendance vis-à-vis du fuseau du navigateur.

Les délais d'envoi, la déduplication et la mémoire Telegram sont conservés.
Aucun message de test n'est envoyé ; les anciens messages ne sont pas réécrits.
Installation et contrôles actifs consignés après livraison.
