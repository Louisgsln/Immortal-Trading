# Lots 129–131 — validation et installation à terminer

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

## Preuves restant à consigner

Tests complets et Node, contrôle de l'image, import sur copie avec notificateur
interdit, aperçu des scores historiques, sauvegarde vérifiée, installation,
préservation des alertes/candidatures/curseur/préférences Telegram, premiers
succès, référence 7/7, HTTPS privé et CI. Aucune source nouvelle n'est déclarée
installée dans ce document avant ces vérifications.
