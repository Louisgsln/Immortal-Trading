# Lot 73 — Dix employeurs finance et trading supplémentaires

Voir les [sources officielles, filtres et limites](EMPLOYER-EXPANSION.md).

## Audit et impact

- Dix collecteurs vérifiés sur leurs catalogues publics : 20 requêtes, 136 offres.
- Sauvegarde locale vérifiée puis restaurée dans une base distincte.
- Deux imports rejoués : 136 ajouts au premier, aucun au second ; aucune
  mise à jour, clôture ou alerte. Les 787 offres existantes restent identiques.
- Leurs candidatures, leurs historiques et les alertes sont conservés.
  Les nouvelles offres reçoivent leur fiche de suivi initiale normale.
- Base simulée : 923 offres, 259 pertinentes et 159 prioritaires.
- Gain des fiches : 65 offres avec missions et 98 avec mentions de diplôme.
  Totaux : 262 avec missions, 304 avec diplôme ; 477 dates de publication connues.
- Les 100 nouveaux tests couvrent chaque identité employeur/URL, les dérives
  de métadonnées, les contradictions campus/stage, les rubriques et les exclusions.

## Validation et installation

Suite complète Windows : 3 790 tests réussis, 4 ignorés.
Ruff, formatage et mypy réussis. Les 923 cartes produisent du HTML valide :
au maximum 1 201 unités UTF-16, sous la limite Telegram.

Commit `5fb7394` publié sur main et installé le 26 septembre à 19:33:50 Paris,
après sauvegarde vérifiée `scheduled-20260926T173344880826Z.zip`. Ancien paquet
et ancienne configuration employeurs conservés. Les réglages existants sont
préservés ; seuls les dix employeurs sont ajoutés à la configuration active.

Les 84 modules installés correspondent au dépôt. Dashboard et API de suivi
répondent correctement. Les dix nouvelles sources ont chacune réussi deux
collectes : 136 ajouts silencieux au premier passage, aucun ajout ni changement
au second. Les scores et candidatures des 787 offres précédentes, ainsi que
les historiques de candidatures et les alertes, sont identiques à la sauvegarde.

Le dashboard actif confirme 923 offres, 259 pertinentes, 159 prioritaires,
262 fiches avec missions, 304 avec diplôme et 477 dates de publication.
Le parcours navigateur vérifie Maven Securities, ses dix résultats, le tri
par publication décroissante et la fiche Graduate Trader Amsterdam : missions,
conditions d'études, date de publication et échéance sont présentes.

À 19:40 Paris, 32 sources sur 34 sont à jour. Nomura campus rencontre encore
un CAPTCHA ; Macquarie attend sa reprise après un compteur de résultats absent
à 19:33, avant l'installation. Les dix nouvelles sources sont toutes à jour.
La reprise Macquarie à 19:44 échoue avec HTTP 302 ; le diagnostic public à 19:46
confirme une redirection vers `recruitment.macquarie.com/en_US/careers/Error`.
Cette réponse du portail n'est pas importée et n'est pas traitée comme une liste
vide. La source conserve ses annonces et réessaiera après la temporisation.
La supervision du processus est saine ; cela ne signifie pas que tous les
portails employeurs sont accessibles. Aucun ancien message Telegram n'est renvoyé.

Les contrôles GitHub Python 3.11–3.14, dashboard Node 22 et construction/restauration
du conteneur ont tous réussi : [exécution du lot](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36259452801).
