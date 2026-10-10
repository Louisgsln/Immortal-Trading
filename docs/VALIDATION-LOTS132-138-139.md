# Lots 132, 138 et 139 — installés et observés sur OVH

Demande : étendre les offres campus/off-cycle des banques US, UK et FR et des
hedge funds, développer le carnet, puis donner la liste et le nombre réellement
suivis par le radar et `/statuts`. Les lots 133–137 conservent leurs tâches ouvertes ;
138 et 139 désignent les fonds et l'inventaire livrés avec l'extension 132.

## Résultat

Profil OVH : **75 sources / 65 employeurs / 74 adresses de catalogue distinctes**,
contre 70 sources / 62 employeurs. Relevé du 10/10/2026 à 18:41 UTC :
**73 à jour, Optiver partiel, BNP Paribas ancien**. Le radar est actif et les cinq
nouveaux connecteurs ont réussi leur premier import. [Liste complète](RADAR-SOURCES-20261010.md).

`/statuts`, `/statut` et `/status` affichent le même total et la fraîcheur ;
`/sources`, `/sources 2`, `/sources 3` donnent l'inventaire de trente sources par page.
Le listener et le Dashboard lisent le même profil de production. Les contrôles
de propriétaire, chat privé, ancienneté des commandes, bot destinataire et curseur
avant réponse restent en place ; aucun message Telegram de test n'a été envoyé.

Image active : `immortal-trading:lot132-campus-funds-20261010`.
Code : `4ce3c4d5a41da70ba38dea969776fa3f3a0d8525`.
Profil public : SHA-256 `efd537fd3312083ab06dfe658b33ae10763c2449df6c1ad536cf337b3d402b79`.

## Ajouts et contrôle des offres

| Source | Catalogue / preuve | Fiches initiales | Score ≥70 | Stages off-cycle/longs 2027 ≥70 |
|---|---|---:|---:|---:|
| Citi campus | Workday public, recherches off-cycle/internship/placement | 17 | 6 | 1 |
| Deutsche Bank campus | Beesite étudiants, 81 programmes publics avant filtrage ; détails et cible Recsolu concordants | 22 | 4 | 0 |
| Lazard campus | Oracle, site étudiant réel CX_2 relié par l'employeur | 4 | 0 | 0 |
| Millennium campus | Eightfold campus, pagination et fiches JobPosting intégrales | 18 | 1 | 0 |
| Capula | Workable public, guide annonçant dix offres et détails Markdown ; vivier spéculatif écarté | 3 | 0 | 0 |

Barclays élargi sur son portail existant : trading, markets, off-cycle, internship,
quantitative et structuring ; 23 fiches au catalogue, huit nouvelles au premier
passage silencieux. Cette extension ne crée ni un nouveau portail ni un employeur.

Les 64 associations des cinq nouveaux périmètres incluent 12 fiches déjà connues
via d'autres sources ; 52 identités supplémentaires. Avec Barclays, la base passe
de 1 374 à 1 434 fiches et suivis. Les scores par source utilisent `job_sources`,
et non le seul collecteur canonique de l'offre ; les fiches Citi communes ne sont
pas dupliquées. Ces chiffres ne sont pas des publications récentes ou un débit hebdomadaire.

Témoin Citi : [Markets — Sales and Trading, Off-Cycle Internship, Paris — France, 2027](https://citi.wd5.myworkdayjobs.com/2/job/Paris--France/Markets---Sales-and-Trading--Off-Cycle-Internship--Paris---France--2027_26992518),
**100/100**, début janvier 2027, six mois selon la description employeur.
Les graduate et postes professionnels de ces sources ne sont pas comptés comme
des stages. Deutsche Bank comprend aussi des internships 2027 bien détectés dont
le format reste inconnu : ils restent hors alertes de stages tant que ce point
n'est pas prouvé. Le QRD Lab Sales and Trading est notamment à 90/100.

La colonne stages exige un internship confirmé, format off-cycle/long, année 2027,
score ≥70 et aucune échéance dépassée ou contradictoire. Elle ne prouve pas
l'éligibilité personnelle ou un envoi :
statut de candidature, fraîcheur, échéance et historique de notification restent
à contrôler. L'aperçu global du Dashboard compte 38 stages satisfaisant ses critères
au relevé ; ce total applique davantage de conditions que le tableau par source.

Millennium Hong Kong off-cycle de 3–6 mois en 2026 est détecté et reste hors
millésime 2027. Pour Deutsche Bank, la phrase précise de conversion CDI conditionnelle
en juillet 2028 est retirée uniquement de l'extraction du début du stage 2027,
avec identité et programme stricts ; description originale conservée, autre année
contradictoire refusée. La référence bancaire antérieure reste retrouvée **7/7**,
dont Bank of America Milan **96/100**. Les missions quantitatives encore non
qualifiées restent au lot 133, sans points attribués au texte général d'entreprise.

## Tests et conservation

- 315 tests ciblés réussis ; régressions Deutsche Bank après normalisation des
  espaces du titre et 74 contrôles Telegram après ajustement du libellé.
  Ruff, format sur 329 fichiers et mypy sur 120 modules réussis.
- CI Python 3.11–3.14 : **5 253 tests par version, couverture 96 %** ; Dashboard : **34 tests**.
  [CI 38076331156](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38076331156) :
  les six contrôles Python, Dashboard et conteneur sont réussis.
- Simulation sur copie, notificateur interdit : cinq sources réussies, 52 nouvelles
  identités, aucune alerte et aucun appel du notificateur ; toutes les anciennes
  candidatures et valeurs de suivi, histoires et identifiants conservés.
  Barclays élargi initialisé silencieusement sur copie puis sur la base active.
- Sauvegarde réelle vérifiée ; même fichier SQLite, schéma 4, intégrité et clés
  étrangères valides. Reconciliation des scores : zéro modification nécessaire.
- Vérification après les cinq imports : toutes les anciennes offres, candidatures,
  notes et statuts conservés ; **48 alertes et 96 entrées d'historique avant/après**.
  Liaison, curseur monotone et préférences du récapitulatif Telegram conservés.
  Les preuves publiques exposent des booléens et compteurs, jamais les identifiants
  Telegram, le curseur, les secrets ou le lien privé.
- Quatre services applicatifs sur l'image 132, Caddy conservé : cinq conteneurs
  en fonctionnement, quatre unités systemd actives et activées. Radar, écouteur
  Telegram et sauvegardes restent autonomes du développement.
- Même lien HTTPS privé modifiable, certificat de confiance, aucune clé Telegram
  dans le Dashboard ; contrat : 86 contrôles, sept modules, assets vérifiés.
  Racine 404, fichier privé 404, POST page 405 et API sans CSRF 403.
  Réponse mesurée : 12,712 s ; optimisation des lectures au lot 135.
- Seuil 70, métiers et géographies conservés ; off-cycle/stages longs 2027 et leurs
  alertes actifs ; Summer hors alertes. Rappels et notifications d'incident restent
  désactivés selon le réglage existant.

Le blocage temporaire de `sudo` dans Remote Desktop Commander a été rétabli :
les 33 commandes initiales sont à nouveau bloquées. La synchronisation des
documents publics se fait ensuite avec Ubuntu, sans accès administratif.

## Limites et prochaines livraisons

La couverture mondiale exhaustive n'est pas prouvée. [L'audit des portails](CAMPUS-FUNDS-AUDIT-20261010.md)
documente Standard Chartered, Lloyds, BPCE/Natixis, Rothschild, Balyasny,
Brevan Howard, Rokos et les accès refusés JPMorgan/NatWest/Citadel/Two Sigma.
Ils ne sont pas déclarés surveillés. BNP français reste refusé en 403 ; son
alternative anglaise demande une adaptation vérifiée. Optiver conserve une lacune.
Nomura campus a repris publiquement ; intervention humaine en attente si CAPTCHA.
Les recherches Workday sont ciblées, pas un inventaire exhaustif de chaque banque.

Le [carnet développé](TASK-BOARD.md) clôture 132/138/139 et détaille 140–145,
avec origine employeur, pagination, témoins et premier succès avant toute activation.
Preuves publiques : [DELIVERY-LOTS132-138-139.json](DELIVERY-LOTS132-138-139.json).
