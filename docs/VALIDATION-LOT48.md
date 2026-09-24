# Lot 48 — Diagnostic BNP et Nomura campus

## Correction du contrôle robots

Le fichier public [robots.txt de BNP](https://group.bnpparibas/robots.txt), lu
le 24 septembre 2026, contient `Disallow: *?$`. Protego 0.6.2 transforme cette
règle en `*$` : même les chemins sans query sont alors refusés. Reproduction
isolée avec cette seule règle et fixture du fichier public complet.

L'adaptateur local `RobotsPolicy` conserve le `?` littéral avant l'ancre finale
et le délimiteur vide dans l'URL comparée. La correction est limitée aux
directives Allow/Disallow standard terminées par `?$` avec un seul `?`.
Les groupes, délais, ordre de priorité et matcher de jokers de Protego sont
conservés. Les URL `?q=`, les autres chemins interdits et une interdiction
générale restent bloqués avant toute requête à la page.

L'adaptateur utilise des structures internes de Protego, isolées dans
`robots.py`. Le lockfile conserve la version 0.6.2 ; ses tests de contrat
devront être exécutés lors d'une mise à jour. Aucun déclassement vers une
ancienne version de Protego ni exception propre à l'hôte BNP.

## Nomura campus

Le portail renvoie HTTP 200 avec une page « Quick Check Needed », un widget
ALTCHA et un formulaire CAPTCHA. Le parseur signale désormais explicitement
un accès restreint, sur le catalogue comme sur les détails. Il ne soumet ni
formulaire ni challenge et ne poursuit pas les fiches après ce résultat.
L'échec conserve le mécanisme existant de temporisation et empêche tout import
ou fermeture d'offres déduite de cette réponse. Ce lot ne rétablit pas l'accès.

## Vérifications

- 2 884 tests réussis sur le paquet Windows installé non éditable, couverture
  96 %, dont 35 nouveaux cas.
- Ruff : 195 fichiers ; mypy : 71 modules applicatifs.
- Contrats HTTP : priorités Allow/Disallow, groupes spécifiques et fusionnés,
  Crawl-delay, règles BNP, délimiteur vide, fragments, encodage et absence de
  requête vers les chemins interdits.
- Nomura : challenge en catalogue et en détail, aucune soumission ni requête
  supplémentaire après détection.

## Vérification publique BNP

Le contrôle robots corrigé permet de lire les recherches et les fiches. Une
seconde anomalie apparaît : plusieurs URL ont le même identifiant employeur
mais un contenu différent. Le garde-fou existant rejette ce snapshot ; aucune
fusion arbitraire ni import partiel n'est effectué. La source ne doit donc pas
être annoncée comme rétablie sur la seule correction robots.

Preuves privées ignorées par Git : `data/windows-service/lot48/`, résultats
`lot48-tests.txt` et `lot48-tests.xml`. La fixture robots publique est versionnée.
