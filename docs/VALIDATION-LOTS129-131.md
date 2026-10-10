# Lots 129–131 — installés et vérifiés sur OVH

Demande du propriétaire : détecter le campus Bank of America et plusieurs banques
comparables, puis intégrer et développer le carnet des tâches.

## Changements

- Lot 129 : Bank of America campus ; catalogue public entier paginé avec `rows`
  comme borne de fin exclusive ; métadonnées, missions, identités, contrat, dates
  et lien de candidature concordants avec la fiche employeur ; premier tableau
  relu avant validation. Workday professionnels reste une source séparée.
- Lot 130 : Jefferies Campus Opportunities, tableau 2, distinct des événements du
  tableau 1 ; détails sans contexte de session conservé ; identité de l'annonce
  et cible publique de candidature vérifiées. RBC, ING, Wells Fargo et Santander
  ajoutés au profil OVH après lecture publique ; requêtes stages/marchés explicites.
- Lot 131 : date du stage séparée des conversions CDI Bank of America revues ;
  mois de début alternatifs conservés ; format off-cycle/Summer lu aussi dans le
  contrat employeur ; Prime Financing reconnu comme securities finance ; rôle
  Jefferies retenu uniquement sur missions et division vérifiées. Mesure de
  couverture alignée sur la politique de collecte des stages et carnet par portail.

Les responsabilités Jefferies qualifiées ne proviennent pas du texte général
sur la banque. Les conversions CDI revues sont retirées uniquement de l'extraction
du début du stage ; les descriptions originales restent conservées.

## Vérifications déjà réalisées

- Milan 15033 : missions employeur réelles, 96/100 ; off-cycle 2027, durée 3–6 mois,
  échéance au jour du 11 octobre 2026 sans inventer d'heure ou de fuseau.
- Londres Prime Financing 14762 : programme de douze mois et contrat off-cycle
  publiés ; conversion éventuelle en CDI en 2029 séparée du stage 2027.
- Jefferies Dubaï 2002 : division Sales and Trading, missions et début alternatif
  janvier/février 2027 confirmés. Le programme Quant Fulltime utilise la valeur
  employeur `Full Time Analyst`, conservée telle quelle.
- Tests ciblés : pagination/endroits/identités, événements, HTTP 403/CAPTCHA,
  détails incomplets, programme Summer, Associate, années contradictoires,
  conversions CDI et qualification des missions couverts.
- Lectures publiques Workday : cinq banques réussies ; leurs compteurs mesurent
  des résultats de recherche distincts, pas une cadence hebdomadaire garantie.

## Livraison vérifiée

Image active : `immortal-trading:lot129-bank-campus-20261010` ; code applicatif `0888b56`, correction du test
concurrent `88b28a8`. Profil public OVH : **70 sources / 62 employeurs** ;
le profil de développement reste distinct. Observé le 2026-10-10T15:09:27.315968+00:00.

Les sept ajouts ont réussi leur premier import de production : **54 fiches**,
dont **13 au seuil de 70**, sans alerte rétroactive. Une fiche retenue ne
prouve pas l'éligibilité personnelle et ces chiffres ne sont pas une cadence
hebdomadaire. Les recherches Workday restent partielles.

| Source | Fiches au premier succès | Score ≥70 | Alertes d'import |
|---|---:|---:|---:|
| rbc | 11 | 1 | 0 |
| wells_fargo | 2 | 0 | 0 |
| ing | 6 | 0 | 0 |
| santander | 11 | 4 | 0 |
| bank_of_america | 11 | 1 | 0 |
| bank_of_america_campus | 10 | 6 | 0 |
| jefferies_campus | 3 | 1 | 0 |

La référence indépendante est retrouvée **7/7** dans la base de production ;
la fiche Milan est aussi vérifiée dans le Dashboard HTTPS.
Le contrôle de référence reste distinct des critères d'alertes et de la fraîcheur
ultérieure des portails.

| Offre témoin employeur | Identifiant | Score |
|---|---|---:|
| Global Markets Sales and Trading 2027 Off-Cycle Analyst - Milan | 15033 | 96 |
| Global Markets Sales and Trading 2027 Off-Cycle Analyst - Stockholm | 15032 | 90 |
| Global Markets Sales and Trading 2027 Off-Cycle Analyst - Frankfurt | 15003 | 96 |
| Global Markets Sales and Trading 2027 Off-Cycle Analyst - Paris | 14724 | 96 |
| 2027 Brazil Fixed Income Sales & Trading Desk Internship Program | 14455 | 92 |
| Prime Financing, 2027 1-Year Placement Analyst - London | 14762 | 84 |
| 2027 Fixed Income Off-Cycle Internship Programme - Dubai, MENA (January/February 2027) | 2002 | 82 |

### Tests et protection des données

- **5 183 tests Python** locaux réussis, couverture 96 %, puis les 23 tests de
  cadence après la correction d'une assertion dépendante du temps de traitement.
  Deux résultats doivent parvenir au consommateur ; une tentative suivante peut
  déjà démarrer avant son signal d'arrêt. L'ordonnanceur n'a pas été modifié.
- **34 tests Node** réussis ; Ruff, format et mypy réussis ; contrat du Dashboard
  dans l'image et en HTTPS : 86 contrôles,
  7 modules, empreintes des assets vérifiées.
- Import sur copie avec notificateur interdit : sept sources réussies, 54 fiches,
  sept témoins, zéro envoi ; toutes les anciennes valeurs de candidatures et
  historiques ainsi que les identifiants des offres sont inchangés.
- Sauvegarde réelle vérifiée avant installation ; même fichier SQLite, schéma 4,
  intégrité et clés étrangères valides. Avant : 1320 fiches,
  1320 suivis, 48 alertes,
  96 entrées d'historique d'alertes.
- Deux champs dérivés de score réconciliés sans création d'alerte ; aucun ancien
  identifiant supprimé, historique d'alertes et de candidatures conservé ; liaison,
  curseur et préférences du récapitulatif Telegram préservés.
- Quatre services applicatifs sur la nouvelle image, HTTPS Caddy conservé ; cinq
  conteneurs en fonctionnement et quatre unités systemd actives et activées.
- Même lien privé HTTPS, certificat de confiance, Dashboard modifiable, aucune
  clé Telegram dans son environnement. Contrôles d'accès : racine 404, fichier
  privé 404, POST de la page 405 et API sans CSRF 403. Réponse mesurée :
  12.549 s ; ce relevé n'est pas une garantie de latence constante.
- Radar et Telegram restent actifs ; off-cycle/longs 2027 et seuil 70 conservés,
  Summer hors alertes. Rappels d'échéance et notifications d'incident restent
  désactivés selon la configuration existante.
- [CI 38061580663](https://github.com/Louisgsln/Immortal-Trading/actions/runs/38061580663) :
  Python 3.11–3.14, Dashboard et conteneur réussis. Le blocage temporaire de
  `sudo` est rétabli après les contrôles de livraison.

Preuves publiques sans identifiants privés : [DELIVERY-LOTS129-131.json](DELIVERY-LOTS129-131.json).
Les sept premiers succès, scores et empreintes du code/profil sont conservés.

### Limites et tâches ouvertes

JPMorgan et NatWest campus restent limités par HTTP 403 ; Nomura campus reste
soumis à intervention humaine, laissée en attente. BNP et les autres incidents
observés restent dans la santé du Dashboard ; aucune santé globale parfaite
n'est revendiquée. Wells Fargo n'a pas de témoin off-cycle 2027 établi ; certains
stages ING/Santander gardent leur année ou format non confirmé. Les rôles quant
non qualifiés ne reçoivent pas artificiellement des points.

Le [carnet principal](TASK-BOARD.md) clôture ces trois lots et réserve les lots
132–137, avec critères de validation : campus complémentaires, missions quant,
dates des stages, performance mobile, suivi hebdomadaire et sauvegarde distante.
