# Lot 70 — Critères d'études Macquarie avec provenance conservée

## Audit des pages publiques

Lecture de 15 annonces publiques le 26 septembre 2026, avec 26 requêtes.
La rubrique **What you offer** comporte deux champs de contenu dans les pages
auditées. Les deux sont conservés ensemble : aucun paragraphe alternatif n'est
écarté. La consigne d'ouverture du volet au clavier est reconnue séparément.

Le contrôle sur l'instance active a révélé des éléments `style` vides sur trois
pages, supprimés par la première capture de fragments. Le collecteur accepte
désormais ces seuls éléments sans attribut et sans contenu ; les styles actifs,
scripts et rubriques masquées restent refusés. Une nouvelle lecture des 15 pages
complètes confirme que les fragments conservés reproduisent exactement les
résultats des anciens et nouveaux collecteurs, y compris ces éléments vides.

La provenance n'est ajoutée que si la rubrique est unique, visible, sans
sous-titre ambigu ni condition extérieure aux champs, et si tous ses champs
de contenu se suivent dans la description. Le contenu d'origine reste identique ;
les métadonnées survivent au stockage sans archive brute. Les anciennes
descriptions sans provenance attendent une collecte réussie.

Cinq annonces donnent des observations dans la limite de 1 500 caractères :

- Graduate Program Commodities/Structuring : Master cité parmi les parcours
  Undergraduate/Masters, avec les conditions de fin d'études et de candidature.
- Delta One Swaps Trader : diplôme quantitatif préféré, explicitement non requis.
- Quantitative Researcher Asia Pacific : diplôme postgraduate sans niveau précis.
- Derivatives Trader/Dealer : qualification tertiaire sans niveau précis.
- Developer Equities Algorithmic Trading : diplôme cité comme avantage.

Aucun Bachelor, Master ou Doctorat n'est déduit d'une qualification générique.
Le profil du Summer Internship dépasse la limite et reste intégralement visible
dans la description. Le filtre Master n'est pas une décision d'éligibilité.

## Répétition sur copie sauvegardée

- Les fragments publics conservés reproduisent exactement les 15 modèles bruts
  de l'ancien collecteur. Le nouveau collecteur ne modifie que la structure de
  la description ; tous les champs métier, le texte visible et les scores sont identiques.
- 787 offres : 192 avec critères d'études, 168 avec missions, 342 dates de publication.
- Deux scans successifs : zéro nouvelle offre, mise à jour, clôture ou alerte.
  Candidatures, historique des candidatures, alertes, historique des alertes,
  versions d'offres et historique des scores strictement identiques.
- Les preuves d'expérience, les dates et les exclusions Associate seuls et stages
  sont conservées. Aucune ancienne fiche n'est artificiellement réévaluée.
- Les 787 cartes Telegram sont identiques et valides ; maximum de 1 170 unités
  UTF-16. Aucun message de test ni réémission d'une alerte.

## Vérifications

- 46 nouveaux tests : rubrique complète, alternatives entre champs, préférences,
  provenance persistée sans archive brute, limites, faux diplômes, contenus masqués,
  styles vides et actifs, sous-titres, texte hors champs, répétition de scan,
  suivi Postulé et protection HTML.
- Parcours navigateur sur copie : Macquarie + Master (une offre, Graduate Program
  à 82/100), puis Diplôme sans niveau précis (quatre offres, détail Delta One
  Swaps Trader à 0/100). Extrait complet et préférence non obligatoire vérifiés.
  Affichage lisible, aucune erreur JavaScript.
- Ruff, formatage et vérification des types réussis. Suite complète Windows :
  3 639 tests réussis, quatre ignorés.

## Livraison

- Code initial `30af1ab` installé à 17:51:39 Paris ; la collecte réelle a révélé
  le cas des styles vides. Correctif `6d0e0ba` publié sur `main` et installé
  le 26 septembre 2026 à 18:06:20, après sauvegarde vérifiée à 18:06:15.
  Paquet précédent conservé, scanner, dashboard et Telegram relancés.
- [CI du correctif](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36254249277)
  réussie : Python 3.11–3.14, 3 643 tests Linux, couverture 96 %, dix tests
  JavaScript sous Node 22 et construction/restauration Docker.
- Collecte automatique Macquarie réussie à 18:15:42 : 15 offres, zéro nouvelle
  offre et zéro mise à jour de contenu. Les cinq mentions sont présentes.
- Contrôle actif à 18:16:56 : 787 offres, 192 avec critères d'études, 168 avec
  missions ; 342 dates de publication connues et 445 inconnues. Les deux fichiers
  applicatifs installés correspondent au code publié ; dashboard et suivi répondent.
- Parcours navigateur actifs réussis : Macquarie + Master (une offre), puis
  Diplôme sans niveau précis (quatre offres), avec les conditions complètes.
  Delta One conserve la préférence « preferred, but not required », son minimum
  de cinq ans et son score nul. Aucune erreur JavaScript. Les exclusions Associate
  seuls, les alternatives Analyst/Associate et le suivi restent vérifiés.
- Scanner et Telegram actifs. À 18:16:56, 23 sources à jour et Nomura campus
  en accès restreint par CAPTCHA. Optiver a repris à 18:11:58 et UBS professionnels
  à 18:12:03 après leurs échecs de pagination ; les nouvelles tentatives restent
  automatiques, sans assouplissement des contrôles.

## Suite du carnet

Continuer l'audit des rubriques BNP en tableau, UBS mixtes et Barclays Tokyo.
Explorer les autres sources et variantes sans tronquer leurs conditions.
Poursuivre l'observation des reprises Nomura et Optiver ; ne pas assouplir les
contrôles de pagination ni contourner les restrictions d'accès.
