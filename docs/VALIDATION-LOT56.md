# Lot 56 — Réparation des sources signalées

## Diagnostic public du 25 septembre 2026

- **BNP Paribas** : 29 offres étaient déjà importées, mais deux références
  conflictuelles empêchaient la validation initiale. « Jamais collectée » décrivait
  l'absence de succès complet, pas l'absence de données.
- **Deutsche Bank / Citi** : leurs résultats Workday contiennent respectivement
  `R0427551` et `26988331`, sans titre ni URL, uniquement `bulletFields`.
  Une recherche publique par référence reproduit exactement cette réponse.
  Une seule ligne interrompait donc toute la collecte.
- **Nomura campus** : la réponse publique contient un formulaire CAPTCHA et
  aucune ligne d'offre. Ce blocage externe reste présent ; aucune collecte
  réussie n'est fabriquée, aucun challenge n'est contourné.

## Corrections

BNP : les variantes doivent toutes pointer explicitement vers la même identité
sur le portail officiel `bwelcome.hr.bnpparibas`. La fiche anglaise liée doit
confirmer l'identifiant canonique et la référence employeur, puis correspondre
à une seule variante par son titre et sa description complète (hors espaces et
entités HTML). Cette variante est retenue sans mélanger les champs des copies.
En cas d'accès indisponible, d'ambiguïté ou de divergence, la quarantaine reste
en place. Les requêtes supplémentaires respectent le budget et les règles robots.

Les références `1234567890100120639` et `BNPSA_242026` sont ainsi résolues à partir
des fiches de recrutement `109680` et `109513`. La copie incorrecte du premier
stage contenait notamment du texte de CDI absent de la fiche de référence.
Les deux offres choisies restent exclues des priorités : stage / internship.

Workday : seules les lignes constituées exactement d'une référence au format
audité chez Deutsche Bank ou Citi sont isolées. Leur position compte toujours
dans la pagination ; doublons, autres malformations et plus de dix références
incomplètes font échouer la collecte. Les offres complètes sont validées puis
importées normalement ; aucune clôture n'est déduite des références incomplètes.
Les alertes des offres complètes gardent les critères habituels.

Le journal conserve `listing_gaps`, sans migration SQLite. Le dashboard et
`/status` distinguent **collecte partielle**, **références contradictoires** et
**accès bloqué par CAPTCHA**. Les deux sources Workday ne sont pas artificiellement
comptées comme entièrement à jour. Une collecte ultérieure sans lacune efface
le diagnostic ; un échec réseau ultérieur reste signalé. L'aperçu d'une collecte
avec lacunes est explicitement `incomplete`.

## Validation sur données publiques et sauvegarde

- BNP : **31 offres**, **81 requêtes**, aucun conflit.
- Deutsche Bank : **26 offres**, **43 requêtes**, une référence incomplète.
- Citi : **50 offres**, **110 requêtes**, une référence incomplète.
- Répétition hors réseau sur sauvegarde vérifiée/restaurée : **784 → 786 offres**,
  deux ajouts BNP, zéro modification métier existante, clôture ou notification.
- Scores existants et candidatures/historiques/alertes préservés. Deuxième
  passage : zéro ajout, modification ou clôture.
- État mesuré sur la copie : **21 sources à jour, deux collectes partielles,
  une source bloquée par CAPTCHA**. Les 24 sources restent surveillées.
- Parcours navigateur Santé des sources vérifié : références Workday et
  explications visibles, BNP à jour, Nomura campus bloqué explicitement.

**3 153 tests Windows réussis, quatre ignorés** (liens symboliques indisponibles),
dont 34 nouveaux tests de réparation. Ruff  formatage et mypy réussis.

## Livraison et contrôle réel

Le code `d1c430b9bf35a10ac73fdad273ee618c966cf370` est publié sur `main` et
installé après sauvegarde vérifiée du 25 septembre à 23:54 Paris. Les dix
fichiers modifiés du paquet installé correspondent au code publié.

La collecte réelle termine en **220,16 secondes** : **234 requêtes, 107 offres,
deux ajouts BNP, zéro modification existante, clôture ou alerte**. BNP, Deutsche
Bank et Citi sont toutes trois à jour. Contrairement à la répétition antérieure,
Workday ne renvoie plus les deux lignes incomplètes ; les recherches publiques
par référence effectuées après la collecte renvoient chacune zéro résultat.
Cette disparition ne constitue pas une preuve de clôture et ne ferme aucune
ancienne annonce. Le traitement des lacunes reste prêt si ce format réapparaît.

Dashboard et API de suivi répondent HTTP 200 ; 786 offres, les 54 extraits de
missions et l'exclusion HSBC Associate sont conservés. Les trois services sont
actifs et les collectes ordinaires ont repris avec succès après la vérification.
Nomura campus demeure explicitement bloqué par CAPTCHA. Au contrôle global,
22 sources sont à jour : un incident UBS professionnels distinct
(`UBS pagination repeated a posting`, observé à 23:52 avant installation)
reste en reprise automatique, en plus de Nomura campus. Il n'est pas masqué.

La [validation GitHub](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36194102648)
est réussie sur Python 3.11 à 3.14, ainsi que pour Docker et la restauration
synthétique. Rapport Python 3.12 : **3 157 tests réussis, couverture 96 %**.
