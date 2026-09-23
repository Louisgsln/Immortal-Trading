# Macquarie : preuve du minimum en sales trading — lot 41

L'offre archivée **23225 — Institutional Cash Equity Sales Trader** énonce cinq
années d'expérience professionnelle en sales trading. Son minimum n'était pas
reconnu dans le corpus audité, où son score était de 71. Une nouvelle extraction
limitée à cette formulation conserve les cinq années, leur origine dans la
description et l'extrait exact qui les justifie.

## Source et portée de la vérification

L'[audit local](../data/discovery/lot41/macquarie-audit.json) établit que les
descriptions des 17 offres Macquarie stockées correspondent aux descriptions de
la capture `data/discovery/lot8/macquarie_collection.json` (SHA-256
`8ebb9ff8fa835a61455db61cd9434d16e4a29cb4069895219cbd6f253a9c6e7e`).
Le quatrième paragraphe de la référence 23225 commence par :

> 5 years’ of experience in sales trading, including client coverage and new business development

Le rejeu local de ces 17 descriptions par le nouveau helper trouve **une seule
preuve**, pour la référence 23225, avec un minimum de cinq ans.

Cette capture conserve la description produite par le collecteur, et non le HTML
brut de la page 23225. Elle n'établit donc pas à elle seule la présence d'un titre
de rubrique dans le HTML original. Aucun téléchargement actuel de cette offre
n'a été effectué pour cette validation. Les autres pages HTML disponibles dans
l'audit appartiennent à d'autres références.

## Extraction bornée

`macquarie_sales_trading_evidence` accepte uniquement le début d'un paragraphe
HTML réel, sous la forme `N years[’'] of experience in sales trading`. Le nombre
est un entier ASCII de 0 à 99 ; les fourchettes, les nombres décimaux, négatifs,
préfixés par zéro et la variante `N+` restent hors de cette nouvelle règle.
Le texte brut sans frontière de paragraphe ne suffit pas.

Le nouvel item `Proven ability` marque la fin de la preuve. Cette frontière
correspond au paragraphe archivé : une préférence de diplôme, beaucoup plus loin
dans les qualifications, ne modifie pas les cinq années demandées au début.
Les préférences, négations, maxima, alternatives académiques ou numériques et
formulations historiques attachés à la proposition examinée la font écarter.
L'apostrophe, la casse et le texte rendu sont conservés dans l'extrait.

La preuve utilise :

```json
{
  "minimum_years": 5,
  "kind": "professional",
  "origin": "description",
  "method": "macquarie_sales_trading_experience",
  "excerpt": "5 years’ of experience in sales trading, including client coverage and new business development"
}
```

Dans le collecteur, cette extraction est appliquée uniquement aux valeurs de la
rubrique validée `What you offer`. Le minimum du résultat reste le maximum entre
les anciennes fourchettes et les nouvelles preuves. Les responsabilités ne
fournissent pas cette nouvelle preuve, et la reconnaissance des anciennes
fourchettes n'est pas élargie. Les limites connues de leur ancienne expression
régulière restent un sujet distinct : ce correctif ne prétend pas les résoudre.

## Validation

Les tests dédiés vérifient le passage du collecteur jusqu'au score et à
l'observation d'expérience, l'extrait exact, la portée de la rubrique, la priorité
d'une ancienne fourchette supérieure, les préférences, les alternatives, les
nombres refusés, le texte masqué et les paragraphes multiples. Les régressions
indépendantes du lot 41 rejouent également la formulation archivée et les limites
du modèle de provenance.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_macquarie.py tests/test_macquarie_sales_experience.py tests/test_experience_provenance_regressions_lot41.py
```

**110 tests ciblés passent** au moment de cette vérification, avec Ruff et mypy
conformes sur les modules Macquarie modifiés. Le rôle synthétique construit avec
le paragraphe archivé porte un minimum de cinq ans et est exclu par la règle
d'expérience existante. Ce test ne vaut pas preuve de modification de la fiche
en service.

Cette livraison de helper et de collecteur ne modifie aucune donnée SQLite. La
simulation de correction du corpus, son application éventuelle et la sauvegarde
qui la précède relèvent du workflow contrôlé du lot et doivent être attestées
séparément.

Le [bilan final du lot 41](VALIDATION-LOT41.md) atteste désormais la sauvegarde,
la répétition, l’application de cette correction à la référence 23225 et les
contrôles d’exports, d’interface et de CI. Les dates de collecte restent inchangées.
