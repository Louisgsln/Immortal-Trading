# Lot 34 — Actifs et termes de profil fondés sur le poste

Travaux du **17 septembre 2026**, avec trois sous-agents : helper de retrait des
passages génériques DRW, audit/régressions indépendantes et stabilisation d'un test
HTTP. L'agent principal a intégré le score, mesuré l'effet, répété le recalcul puis
appliqué la correction.

## Résultat

Deux passages de présentation générale DRW attribuaient les marchés de l'entreprise
à chacun de ses postes. Ils sont désormais retirés de la seule vue de texte
utilisée pour les actifs et termes de profil. **Neuf scores totaux changent**,
tous chez DRW. Les **787 offres des autres sources sont inchangées**.

| Offre | Score avant → après |
| --- | ---: |
| Floor Trader | **94 → 82** |
| Quantitative Trading Analyst, deux offres | 96 → 84 chacune |
| Quantitative Trading Analyst - GD1 | 88 → 76 |
| Equity Dispersion Trader | 77 → 75 |
| Data Analyst - Global Markets and Equities | 76 → 74 |
| Equity Index Voice Trader | 70 → 68 |
| US Equity Index Options Trader | 73 → 71 |
| Associate Trader | 72 → 70 |

Floor Trader conserve son **indice junior et ses 20 points junior** du lot 33.
Ses douze points retirés provenaient d'actifs cités uniquement dans le texte du
groupe (dix points) et du terme FX (deux points de profil). Python reste reconnu.
Le département Options présent dans la capture n'est pas utilisé comme preuve
implicite dans les données stockées. L'offre reste au-dessus du seuil de priorité 70.

Les 27 offres DRW reçoivent une explication de portée ; 25 listes d'actifs et
24 listes de termes de profil changent. Les scores totaux des 15 offres DRW
déjà exclues restent à zéro. Un score inchangé peut donc conserver un événement
de recalcul pour refléter les nouvelles explications et catégories.

Base finale : **814 offres, 812 actives, 163 scores actifs ≥70 et 250 ≥55**.
Une offre passe sous le seuil 70 ; le nombre d'offres et de scans reste inchangé.

## Périmètre vérifié

- Deux signatures textuelles complètes : paragraphe des implantations et marchés
  DRW dans 26 descriptions ; introduction de Prediction Markets Trader dans une.
- Identité DRW vérifiée conjointement par employeur, nom normalisé, clé source
  `drw` et type `official`.
- Ponctuation et mots exacts, avec tolérance sur les espaces et retours à la ligne.
  Les formulations proches ou inconnues sont conservées.
- Aucune troncature après une rubrique About ou une introduction : les missions
  peuvent suivre le texte général, comme dans 21 des descriptions examinées.
- Le titre reste inclus dans le classement ; les preuves de marché dans les
  missions et exigences avant/après sont conservées.
- Les règles de séniorité, expérience, début, Front Office et exclusions gardent
  le texte complet. Les descriptions stockées et affichées ne sont pas réécrites.

L'[audit indépendant](DRW-EVIDENCE-AUDIT-LOT34.md) détaille les signatures, les
27 comparaisons et les cas conservant FX ou Options grâce au poste lui-même.
Cette correction n'élimine pas toute mention générique chez tous les employeurs.
`UNKNOWN` désigne l'absence de terme d'actif reconnu dans la vue filtrée, sans
prétendre que le poste ne traite aucun actif.

## Mesure, répétition et préservation

La référence a été prise avec le paquet non éditable du lot 33. Le nouvel aperçu
`rescore --dry-run` évalue les 814 offres : **27 recalculs, neuf scores totaux
modifiés**, tous DRW. L'audit indépendant obtient les mêmes listes et scores.
Les points trading, junior, début, Front Office et exclusions restent identiques.

- Sauvegarde vérifiée : `data/backups/lot34-before-drw-evidence.zip`.
- Restauration vers `data/discovery/lot34/rehearsal.db`, onze tables initialement
  identiques à la base active.
- Répétition puis application : 27 versions `rescored` et 27 entrées de score
  ajoutées, historiques antérieurs conservés.
- **Huit tables intégralement préservées** : candidatures et historique, alertes
  et historique, sources, scans et schéma.
- Dans les offres, seuls `asset_class` et `score_breakdown` changent ; le score
  SQL est synchronisé. Descriptions, identités, dates d'observation et état actif
  sont conservés. Les 787 autres lignes restent exactement identiques.
- Second passage : zéro modification. Toujours 46 scans métier et aucune alerte.
- CSV et dashboard réexportés ; nombre d'offres et score 82 de Floor Trader
  contrôlés dans les deux fichiers. Pas de nouvelle inspection visuelle.

## Validation

- **2 012 tests réussis**, soit 54 nouveaux ; couverture Python **96 %**.
- 35 tests du helper, 18 régressions indépendantes du scorer, un parcours CLI
  aperçu/recalcul/répétition avec descriptions, dates, candidature et alerte préservées.
- Ruff : **156 fichiers** conformes ; mypy : **63 fichiers**, sans erreur.
- Reconstruction hors réseau depuis `uv.lock`, suite complète sur installation
  non éditable. Aucune dépendance, migration ou configuration métier modifiée.

La première suite complète a rencontré un abandon de connexion Windows dans
le test HTTP existant qui envoyait un formulaire trop volumineux. Le serveur
rejette sa taille avant lecture du corps ; la fermeture pendant l'envoi peut
empêcher le client de lire le statut. Le test isolé passait. Le contrôle a été
stabilisé pour vérifier le rejet dès les en-têtes, sans masquer d'exception ni
ajouter de retry. Le serveur de production n'est pas modifié ; la suite complète
a été relancée après cette correction du test.

Preuves locales sous `data/discovery/lot34/` : `before.json`, `scoring-before.json`,
`impact.json`, `quality-audit.json`, `rehearsal.json`, `apply.json`, `exports.json`,
`post-apply-rescore.json`, `test-results.xml` et `test-results.txt`. `workflow.py`
conserve le script ponctuel et ses contrôles ; ces artefacts sont exclus de Git.
`test-results-first.txt` et `.xml` conservent aussi le premier échec HTTP.

Aucun réseau, notification, candidature envoyée, watcher ou déploiement lancé.
La validation Docker/VPS et la copie distante des sauvegardes restent séparées.
