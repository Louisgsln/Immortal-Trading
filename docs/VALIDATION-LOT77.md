# Lot 77 — Heure de Paris et avis Telegram épurés

Demande du 26 septembre 2026 : utiliser Paris dans les affichages et raccourcir
les notifications d'incident et de retour à la normale.

## Comportement

- Dashboard, fiches, échéances, historique, santé des sources, listes Telegram,
  récapitulatif et notifications : horaires Europe/Paris avec UTC+2 en été et
  UTC+1 en hiver. Le fuseau du navigateur ne change plus le résultat.
- Publications, filtres de dates, actions échues et tendances : journées de Paris.
  Les journées de 23 et 25 heures sont comptées selon leur calendrier local.
- CSV : instants ISO avec le décalage de Paris. Les dates sans heure restent
  des dates sans heure ; les instants stockés en base restent inchangés.
- Avis automatiques : trois sources au maximum, cause et reprise possible,
  synthèse des sources, horodatage Paris et accès à `/status`.
- Retour à la normale : trois lignes de contenu. `/status` conserve les horaires,
  le seuil, les compteurs et jusqu'à huit sources ; le dashboard détaille le reste.
  Les erreurs de base, d'activité du collecteur et de livraison restent explicites.
- Les délais, la déduplication, le curseur Telegram, les boutons de candidature,
  les règles de score et les collecteurs restent inchangés. Aucun envoi de test
  ni rejeu d'ancienne alerte. Les anciens messages ne sont pas modifiés.

## Vérifications locales

3 945 tests validés, quatre ignorés : suite complète, puis reprise des deux
assertions qui attendaient l'ancien libellé CAPTCHA et le fuseau UTC du rapport
de tendances. Les 125 tests de contrôle Telegram, incidents, reprise des sources
et commande de tendances passent après correction. Mypy : 87 modules ; Ruff et
formatage : 240 fichiers. Les onze tests JavaScript passent.

Les scénarios couvrent minuit, été/hiver, heure manquante au printemps et heure
répétée en automne, navigateurs UTC/Honolulu/Paris/Kiritimati, dates inconnues,
CSV, limites Telegram en UTF-16, incidents non liés aux sources et absence de
fausse confirmation lorsque les alertes sont désactivées. La mémoire d'envoi
et l'absence de réexpédition après redémarrage restent testées.

L'aperçu local en lecture seule affiche les 973 offres : en-tête Paris (UTC+2),
horaires des sources lisibles et graphiques regroupés par jour de Paris.
L'aperçu n'a effectué aucune écriture de suivi ni aucun appel Telegram.

## Livraison

Publié sur `main` : `8311a067051574c3c2d74fcc7e131e53760db9ac`. Installé le 26 septembre 2026
à 21:41 Paris (UTC+2), après sauvegarde vérifiée
`scheduled-20260926T194152213358Z.zip`. Les 92 fichiers applicatifs et ressources
installés correspondent au paquet construit. Scanner, dashboard et Telegram relancés.

Contrôle à 21:43 Paris (UTC+2) : collecteur actif, cinq sources ont déjà réussi
après installation. Dashboard et API de suivi répondent ; 973 offres et
175 priorités. Scores, candidatures, historique et alertes identiques à la
sauvegarde prise juste avant installation. Le curseur Telegram est conservé,
le dernier avis automatique reste celui de 21:11 Paris ; aucun renvoi au redémarrage.

39 sources sur 40 sont à jour à ce contrôle. Nomura campus reste limité par
un CAPTCHA ; sa reprise possible est affichée à 22:04 Paris (UTC+2). Ce lot
modifie la présentation des incidents et ne contourne pas la restriction.

L'en-tête et les horaires du dashboard ont été vérifiés dans le navigateur,
ainsi que les libellés des journées de tendances. Recharger les anciens onglets
pour charger les nouveaux formats. Les anciens exports HTML et messages
Telegram conservent leur présentation d'origine.

Python 3.11–3.14, les onze tests JavaScript et la construction/restauration
isolée du conteneur ont tous réussi en [CI](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36266935412).
