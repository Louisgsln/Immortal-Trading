# Validation du lot 106

Les diagnostics OVH transmis le 6 octobre identifient une date de début CA CIB
incompatible, une adresse HSBC incomplète, un niveau IMC inconnu et un échec de
pagination SIG. BNP renvoie HTTP 403 et Nomura demande un CAPTCHA. Les valeurs
des trois champs et le contrôle exact SIG ne figurent pas dans ce premier relevé.

## Changements vérifiés

- SIG relit un catalogue instable une seule fois, depuis la première page, dans
  le budget de temps existant. Les validations de pagination restent actives et
  les résultats d'une tentative rejetée sont écartés. Les compteurs de requêtes
  incluent toutes les tentatives.
- IMC classe explicitement un niveau de type liste comme `SourceUnavailable` ;
  la liste des niveaux autorisés reste la même.
- `scripts/probe_source_fields.py` inspecte les champs concernés avec les
  collecteurs actuels et produit des exemples publics bornés. Il ne lit aucune
  base et n'instancie aucun notifier. Les services et états ne sont pas modifiés.
  HTTPS, robots et rythme des requêtes sont conservés ; les limites sont de
  120 secondes et 40 requêtes par source. Les accès candidat et autres hôtes
  sont refusés et les URLs, emails et formes de tokens sont masqués.

## Vérifications locales

201 tests ciblés passent : collecteurs IMC, SIG, CA CIB et HSBC, extraction des
preuves et six tests de reprise d'alertes et de commandes Telegram. La reprise
SIG est testée sur changements transitoires, échecs persistants, page mal formée,
compteurs et expiration du budget commun. Les tests d'extraction interdisent
SQLite, les notifications et les commandes de service.

Les 14 tests du helper passent aussi en important exclusivement les sources du
commit du lot 103, `3afcdbf7b9e1f2ba5e951238d3317d5685fddbf3`, dans un répertoire
temporaire. Cette compatibilité est vérifiée hors réseau, sans prétendre avoir
exécuté une collecte réelle sur le VPS.

Ruff, format (287 fichiers), mypy (101 fichiers source) et contrôle du diff passent.

## Validation distante restante

Le helper peut être transmis via stdin au conteneur déjà déployé, en laissant
scanner et Telegram actifs. Il ne met pas à jour cette image. Les champs réels
doivent être récupérés avant de modifier leurs interprétations métier. Aucun
jour, pays ou niveau Graduate n'est supposé à partir du seul message d'erreur.

La reprise SIG et le garde-fou IMC demandent une livraison d'image distincte
après validation de la CI. BNP et Nomura restent des problèmes d'accès public ;
ce lot ne contourne pas leurs refus.
