# Lot 86 — Catalogue Marex et fiches de marché

Le catalogue officiel Marex est ajouté aux sources du radar, avec un passage
toutes les **30 minutes**. Les 75 cartes publiées sont contrôlées avant de retenir
les titres trading, quantitatifs, structuring, courtage, FX Dealer, ventes de
matières premières et exécution. Les exclusions de titre évitent les fiches
senior, opérations, conformité, développement logiciel et fonctions de support.

## Fiabilité et contenu

- Total du catalogue comparé au nombre de cartes ; identifiants uniques et
  adresses limitées au site officiel. Limites : 500 cartes, 60 fiches et 600 secondes.
- Titre, lieu, département, contrat et lien de candidature Breezy de chaque fiche
  doivent correspondre à la carte. Une fiche incohérente invalide toute la collecte.
- Nouvelle lecture du catalogue après les fiches : une simple permutation est
  acceptée ; une variation de contenu reporte l'import, sans écriture partielle.
- Client habituel du radar : robots.txt, espacement de deux secondes, délais,
  restrictions d'accès et reprises réseau bornées. Aucune session nécessaire.
- Descriptions conservées avec paragraphes et listes ; scripts, liens intégrés
  et contenus cachés ne deviennent pas des missions. Six fiches possèdent une
  rubrique de missions reconnue. Les rubriques Skills and Experience sont
  disponibles pour les mentions de diplôme, sans en inventer lorsqu'elles manquent.
- Périmètre filtré : aucune fermeture déduite d'une absence. Les dates de publication
  sont lues dans les données JSON publiques intégrées à la page, sans exécuter
  de JavaScript. Chacune est reliée à son identifiant, titre, lieu, contrat et
  employeur ; les dates imprécises, sans fuseau ou invalides sont rejetées.
  Les neuf dates sont disponibles dans les tris habituels du dashboard, en
  heure locale sans mention du fuseau.

## Mesure sur copie

Deux collectes réelles : **12 requêtes chacune**, **9 nouvelles fiches**, dont
**2 au seuil de 70**, six avec missions et neuf avec date de publication. Les **991 offres antérieures** gardent
leurs scores ; candidatures, historiques et alertes sont préservés. Le premier
import est silencieux, même avec les alertes activées : **aucune alerte créée**.
Le second passage est également silencieux.

| Poste | Score | Lecture |
| --- | ---: | --- |
| Agricultural Trading Assistant | 77 | Poste présenté comme junior front office, avec support du desk et progression conditionnelle vers le trading |
| Securities Finance Trader | 71 | Expérience du domaine demandée sans minimum chiffré ; le score ne garantit pas l'éligibilité d'un débutant |
| Precious Metals Physical Trading Specialist | 0 | Dix ans d'expérience demandés |
| Trois postes Commodity/Cross Commodities Sales | 0 | Vente pure exclue |
| Deux FX Dealer et Metals Execution Specialist | 0 | Pas de nouvelle règle globale de qualification ; missions à auditer séparément |

Le programme UK Graduate 2027 n'est pas ajouté : il est absent du catalogue
actuel et sa fiche indique une clôture au **21 septembre 2026**, déjà dépassée
lors de la vérification du 27 septembre. La page générale le présentant comme
ouvert ne suffit pas. Aucun formulaire de candidature ou de notification envoyé.

Sources officielles : [catalogue](https://www.marex.com/careers/career-opportunities),
[Trading Assistant](https://www.marex.com/careers/career-opportunities/8ac5c23bf47e01-agricultural-trading-assistant),
[Securities Finance Trader](https://www.marex.com/careers/career-opportunities/73602d77d7c401-securities-finance-trader),
[programme Graduate](https://marex.breezy.hr/p/86dc2823d7d601).

## Validation et installation

44 tests ciblés réussis : catalogue incomplet, doublons, restrictions d'accès,
identité et métadonnées divergentes, changement de catalogue, limite de détails,
contenus masqués, rubriques, dates et exclusions Associate/stage/expérience.
L'exercice de restauration a aussi été corrigé : ses sous-processus utilisent
un dossier temporaire dédié. Si le dossier système est inaccessible, Python
ne crée plus ses fichiers temporaires directement dans le dossier audité.
La protection qui détecte une modification du dossier de sauvegarde reste
active. L'échec Windows initial a été reproduit puis le scénario complet réussit.
Suite complète : **4 096 tests réussis, 4 ignorés**. Lint et format des
252 fichiers réussis, analyse statique des 91 modules réussie. Le paquet construit
contient 96 fichiers applicatifs vérifiés contre les sources. La vérification de
l'installation sera consignée ci-dessous après déploiement. Vitol et Trafigura
restent à intégrer.
