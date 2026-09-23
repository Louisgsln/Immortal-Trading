# Lot 41 — Provenance Crédit Agricole CIB et minimum Macquarie

Audits préparés le 17 septembre et validation finale le **23 septembre 2026**.
Des sous-agents ont travaillé sur les collecteurs, les audits indépendants et
les parcours navigateur ; intégration, mesure et correction par l’agent principal.

## Résultat

| Périmètre | Correction | Effet sur le score |
| --- | --- | --- |
| 21 offres Crédit Agricole CIB | Preuve du champ employeur dédié, avec valeur exacte et origine explicite ; minima conservés. | Aucun |
| Macquarie `23225`, Institutional Cash Equity Sales Trader | Cinq ans professionnels reconnus, avec extrait de la description et provenance. | 71 → 0, exclusion d’expérience existante |
| 16 offres Nomura professionnels auditées | Sept minima reproduits ; aucune erreur réelle démontrée, limites synthétiques documentées. | Aucun changement |

Le corpus compte **814 offres, dont 812 actives, 239 pertinentes et 160
prioritaires**. Parmi les actives, **71** ont un minimum de 0–2 ans, **185**
un minimum supérieur à deux ans et **556** un minimum non reconnu.

Ce lot corrige les données à partir des **captures conservées**. Il ne constitue
pas une nouvelle collecte : descriptions, dates d’observation et fraîcheur des
sources restent identiques. Le classement ne prouve donc pas que chaque offre
est encore ouverte le 23 septembre.

## Provenance et portée

- Crédit Agricole : seules les valeurs du champ nommé
  `fldapplicantcriteria_experiencelevel` fournissent une preuve `employer_field`.
  L’archive doit reproduire exactement l’identité et la description stockées.
  Neuf minima zéro, deux minima trois, huit minima six et deux minima onze
  sont conservés. Les trois offres sans ce champ ne reçoivent aucune preuve.
- Macquarie : reconnaissance limitée au début d’un paragraphe demandant
  `N years[’'] of experience in sales trading`. Les préférences, négations,
  alternatives et contextes non obligatoires examinés sont écartés.
  Le collecteur applique cette règle dans `What you offer` ; la correction
  historique utilise le paragraphe conservé, dont l’ancien titre de rubrique
  n’est pas disponible. Les anciennes fourchettes restent indépendantes.
- Le modèle valide ensemble méthode, origine et cadre. Le dashboard distingue
  un champ publié par l’employeur d’une durée déduite de la description ; il
  conserve les preuves Jump et affiche les extraits comme du texte.
- Aucune migration SQLite n’est nécessaire. Les anciens JSON sans preuve restent
  lisibles ; une preuve n’est pas inventée lors de leur lecture.

Audits : [Crédit Agricole CIB](CA-EXPERIENCE-PROVENANCE-LOT41.md),
[Macquarie](MACQUARIE-EXPERIENCE-PROVENANCE-LOT41.md) et
[Nomura](NOMURA-EXPERIENCE-PROVENANCE-LOT41.md).

## Correction et validation

La revue indépendante a recalculé les **814 offres** et approuvé l’impact
`ecc5454e56b2f2ef0f23e1091ab0211d74a32fada0cb24e563d11bbb84233b46`.
Les empreintes des archives et les onze tables initiales concordent.

La sauvegarde `data/backups/lot41-before-ca-macquarie-experience.zip` a été
restaurée dans une base distincte, puis la correction y a été répétée avant
application réelle. **22 lignes d’offres changent, une seule décomposition et
un seul total changent ; 792 lignes restent strictement identiques.**
Vingt-deux versions et entrées d’historique de score sont ajoutées. Huit autres
tables, dont les candidatures, les alertes et les scans, restent identiques.
Le deuxième passage est sans effet. Le recalcul ordinaire `rescore --dry-run`
évalue ensuite 814 offres et annonce zéro changement.

Les **814 lignes CSV et fiches HTML** correspondent à la base corrigée pour les
scores ; les descriptions et indicateurs d’expérience du HTML concordent aussi.
Le serveur local utilise le paquet installé reconstruit. L’export indique zéro
source fraîche : cette mesure hors ligne ne renouvelle pas leur date de collecte.

**2 587 tests réussis**, soit 149 de plus que le lot 40, sur le paquet installé
non éditable sous Windows Python 3.14 ; **96 % de couverture**. Ruff et le
formatage passent sur 179 fichiers, mypy sur 69 fichiers dont quatre scripts.
La syntaxe JavaScript est vérifiée. Après ce passage, seul le garde JavaScript
exigeant une méthode de preuve de type chaîne a été ajouté ; le paquet a été
reconstruit pour la vérification navigateur.

Edge vérifie l’export HTML et le serveur local : seuils et trois catégories
d’expérience, preuves Jump conservées, champs Crédit Agricole à zéro et six ans,
Macquarie à cinq ans et score nul avec exclusion explicite. Les deux surfaces
passent aussi à 390 pixels sans débordement horizontal ; les captures sont
contrôlées visuellement. Vingt variantes synthétiques couvrent les données absentes
ou mal formées, les couples méthode/origine invalides, la coercition d’une méthode
non textuelle, les propriétés de prototype et les tentatives d’injection HTML.
Les preuves invalides sont ignorées, les extraits valides restent du texte et
aucune erreur JavaScript n’est observée.

La [CI du lot 41](https://github.com/Louisgsln/Immortal-Trading/actions/runs/35921152392)
est réussie pour le commit `16322861f05f7a2f7c8c49918213e50220f6602e`.
Les versions Python **3.11 à 3.14** passent chacune les **2 587 tests**, avec **96 % de
couverture**. Le build Docker, l’entrée de commande et l’exercice de reprise
réussissent : UID **10001**, réseau coupé, **onze tables restaurées identiques**.
Les cinq logs sont conservés dans les preuves locales. Docker est validé sous
Linux en CI ; l’activation de WSL et l’exploitation Docker sur le poste Windows
restent à terminer.

## Preuves locales

`data/discovery/lot41/`, hors Git, conserve les audits, empreintes initiales,
rejeu des 814 offres, impact, revue indépendante, répétition sur sauvegarde,
application, contrôles d’exports, résultats pytest et parcours navigateur.
Les descriptions et données personnelles ne sont pas publiées dans le dépôt.
