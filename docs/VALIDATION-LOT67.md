# Lot 67 — Missions et diplômes BNP Paribas

## Périmètre audité

Les 31 fiches BNP Paribas conservées ont été inspectées. Les observations se
limitent aux listes adjacentes aux rubriques employeur vérifiées :

| Usage | Rubriques |
| --- | --- |
| Missions | Direct Responsibilities, Main Responsibilities, Principal Role Accountabilities, Your Main Activities Are, What you will do |
| Diplômes | Profile and Skills to Success, To be considered for the placement, you will, What is required for you to succeed?, Your profile, Essential, Technical & Behavioral Competencies, Requirements |

Les trois premières missions complètes et leur rubrique sont visibles dans le
dashboard ; les prochaines alertes éligibles utilisent les extraits avec leurs
limites habituelles. Les parcours conditionnels Sales/Trading des programmes ne
sont pas choisis arbitrairement. Les rubriques multiples, tableaux et descriptions
sans liste adjacente reconnue restent accessibles dans la description complète.

La formulation commençant par **Master in** est reconnue uniquement dans les
critères BNP audités. Les alternatives, disciplines et préférences sont conservées.
La mention d'un Master parmi des parcours Graduate/Undergraduate/étudiant en
Master ne devient pas un minimum exigé. BTech et MTech restent dans l'extrait
lorsqu'un autre diplôme explicite est cité, sans Bachelor ou Master attribué
par équivalence supposée.

## Impact sur sauvegarde restaurée

- 787 offres, dont 31 BNP : dix nouvelles fiches avec missions et onze avec diplômes.
- Couverture totale : 168 missions et 149 mentions de diplôme ; toutes les
  observations des sources précédemment couvertes sont conservées.
- Les 11 tables et les modèles d'offre sont identiques avant et après lecture :
  scores, candidatures, dates, alertes et historique inchangés.
- Les 787 cartes Telegram restent valides, avec un maximum de 1 170 unités UTF-16.
  Aucune ancienne alerte réémise.
- Les exclusions Associate seuls et stages, comme les titres explicitement
  ouverts aux deux niveaux Analyst/Associate, gardent leur comportement antérieur.

## Vérifications locales

- 38 tests ajoutés : rubriques, conditions des missions, listes imbriquées,
  alternatives académiques, absence d'équivalence supposée, limites des sources,
  contenus masqués, structures ambiguës, limites Telegram et suivi Postulé.
- Parcours navigateur sur copie : BNP + Bachelor (deux offres), détail FX
  Derivatives Trading Assistant Manager (75/100) ; BNP + Master (huit offres),
  détail Graduate Programme Hong Kong (84/100). Missions et preuves visibles,
  alternatives conservées ; aucune erreur JavaScript.
- Suite complète Windows : 3 515 tests réussis, quatre ignorés. Ruff, formatage
  et vérification des types réussis.

## Livraison

Publication, installation et contrôles GitHub à consigner après la validation locale.

## Suite du carnet

Poursuivre l'audit des employeurs et des variantes encore non reconnues, notamment
les tableaux BNP, les rubriques UBS mixtes et Barclays Tokyo. Qualifier séparément
les rôles hybrides et maintenir l'observation des sources. La copie distante des
sauvegardes attend toujours une destination choisie.
