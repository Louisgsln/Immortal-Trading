# Lot 57 — Diplômes Nomura avec leur contexte

## Périmètre

Le filtre « Diplôme mentionné » et le détail du dashboard prennent maintenant en
charge le champ **Position Specifications → Qualification** de Nomura professionnels.
Les quatre champs du tableau doivent être présents dans leur ordre observé,
avec une fin explicite à la rubrique des responsabilités. Le numéro de réquisition,
lorsqu'il existe, reste hors de l'extrait. Les contenus cachés, tableaux répétés,
champs ambigus et sections trop longues ne sont pas interprétés.

L'extrait complet conserve alternatives, préférences et négations. Il ne fournit
ni diplôme minimum ni décision d'éligibilité. Les qualifications génériques,
MBA, Graduate/Post Graduate et certifications ne sont pas converties en niveaux
académiques. Les autres rubriques Nomura et le portail campus restent hors périmètre.

## Mesure sur sauvegarde restaurée

Audit du 26 septembre 2026, 786 offres dont 16 Nomura professionnels :

- Quatre nouvelles observations : `1373072800` (Master, Doctorat),
  `1405548900`, `1372610900`, `1397978500` (Bachelor, Master).
- Les 30 observations DRW/IMC sont identiques à la version précédente.
- Les 11 tables de la copie restent identiques après génération du dashboard.
  Aucun score, candidature, historique ou état d'alerte n'est modifié.
- La source originale reste accessible dans chaque fiche.

## Vérifications

- 31 nouveaux cas automatisés : variantes observées, alternatives à l'expérience,
  préférences, négations, contexte d'entreprise, rubriques incomplètes, ambiguïtés,
  bornes de taille, texte caché, HTML échappé et conservation de la base.
- Parcours navigateur sur copie : Nomura + Doctorat retourne une offre ;
  Nomura + Master retourne quatre offres. Le détail montre le champ d'origine
  et l'alternative au diplôme. Aucun message d'erreur JavaScript observé.
- Suite complète Windows : 3 184 tests réussis, quatre ignorés. Ruff et
  vérification des types réussis.
- [CI du lot](https://github.com/Louisgsln/Immortal-Trading/actions/runs/36196242858)
  réussie sur Python 3.11–3.14 et Docker : 3 188 tests Linux, couverture 96 %,
  construction du conteneur et exercice de restauration sans réseau réussis.

## Livraison

- Code publié directement sur `main` : `177c734`.
- Sauvegarde vérifiée le 26 septembre à 00:21, version précédente conservée,
  puis installation du paquet isolé et contrôle des trois fichiers livrés.
- Dashboard et lecture du suivi de candidature répondent correctement ;
  786 offres, 34 mentions de diplôme, 54 extraits de missions et six preuves
  d'expérience Nomura vérifiés sur l'instance active.
- Exclusion HSBC Associate seul et conservation des titres mixtes Analyst/Associate
  vérifiées. Scanner, dashboard et Telegram redémarrés ; nouvelles collectes
  Jump et XTX réussies après installation.

## Prochaine étape

Étendre les rubriques de diplôme ou de missions uniquement après audit d'un
autre employeur. L'incident de pagination UBS observé au lot 56 s'est résorbé
sur la collecte du 26 septembre à 00:15 (34 offres). Nomura campus reste sous
restriction d'accès ; ce lot ne modifie pas ses contrôles.
