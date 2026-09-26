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

Publié sur `main` : `61352a1475ea8e519faeea62df80c1638e6bf009`. Installation le
26/09/2026 · 21:57, après sauvegarde vérifiée
`scheduled-20260926T195737250151Z.zip`. Les 92 fichiers du paquet installé sont vérifiés.

Contrôle à 21:58 : scanner actif, six sources déjà recollectées depuis
l'installation, dashboard et API de suivi disponibles. Les 973 offres,
175 priorités, candidatures, historiques et alertes sont préservés. L'état
Telegram conserve le dernier avis automatique de 21:11 : aucun rejeu.

Vérification dans le navigateur : l'en-tête affiche `26 sept. 2026, 21:59`.
Le rendu local du message d'incident affiche
`Reprise possible dès 26/09/2026 · 22:04`, sans suffixe de fuseau.
Recharger les onglets déjà ouverts pour bénéficier de ce format.

Les suites Python 3.11–3.14, les onze tests JavaScript et la construction/restauration
isolée du conteneur ont tous réussi en [CI](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36267830641).
