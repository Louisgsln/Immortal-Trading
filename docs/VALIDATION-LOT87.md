# Lot 87 — TotalEnergies, ENGIE et EDF Trading

Trois employeurs sont ajoutés au périmètre trading et marchés de l’énergie,
avec un intervalle de **30 minutes** et deux secondes minimum entre requêtes
sur un même site. Le périmètre configuré atteint **47 sources / 42 employeurs**.
Le premier import reste silencieux, même avec les alertes activées.

## Collecte et limites

- **TotalEnergies** : catalogue Avature officiel, quatre recherches (`trading`,
  `trader`, `quantitative`, `structuring`), pagination de 20 cartes. Contrôle des
  bornes, du total, des identifiants et des doublons ; deuxième lecture complète
  après les fiches. Les renvois Oracle observés sur certaines cartes hors cible
  sont reconnus sans visiter ces formulaires. Identité, pays, contrat, entité et
  lien de candidature sont recoupés sur chaque fiche sélectionnée.
- **ENGIE** : le sitemap public est lisible, alors que robots.txt interdit
  l’API `/services/` de recherche. Seuls sitemap et pages d’offres autorisées
  sont utilisés. Deux redirections maximum, uniquement HTTPS sur le même domaine
  et dans `/job/`, avec robots et espacement appliqués à chaque destination.
  Les nouvelles références de recrutement sont recoupées avec la fiche, son URL
  canonique et ses liens de candidature. Les variantes de langue ne créent pas
  plusieurs offres ; seules les versions `en_US` sont retenues. Le sitemap peut
  publier une offre avec retard et ne garantit pas une couverture exhaustive.
- **EDF Trading** : portail Workday lié depuis le site employeur, collecteur
  existant avec recherches bornées et contrôle des détails. Aucun nouvel accès
  authentifié ou abonnement n’est nécessaire.
- Limites : 500 résultats par recherche TotalEnergies/EDF, 5 000 entrées dans
  le sitemap ENGIE, 80 fiches sélectionnées et 600 secondes par collecte.
- Périmètres filtrés : aucune fermeture déduite d’une absence. Une restriction,
  un changement du catalogue ou une identité divergente invalide la collecte ;
  aucun résultat partiel ne devient un succès. Aucun assouplissement global du
  ciblage : Associate seul, stages et postes trop expérimentés restent exclus
  des alertes ; Analyst/Associate reste admissible.

## Fiches et dates

Les rubriques du descriptif sont conservées sans scripts ni contenu masqué.
Des titres de missions et qualifications observés sur ces trois portails sont
ajoutés à l’extraction existante, sans modifier les scores antérieurs.
Le champ Experience de TotalEnergies apporte une preuve explicite lorsque sa
valeur est « Minimum N years » ; elle reste visible avec sa provenance.

TotalEnergies et ENGIE donnent des jours de publication sans heure. Un champ
distinct conserve cette précision, sans fabriquer un instant à minuit. Il est
pris en charge par la base, le dashboard, le CSV, l’aperçu des changements et la
notification textuelle. Les tris et filtres calendaires existants fonctionnent
avec ces dates. La date de découverte n’est jamais substituée à la publication.

Le programme Trading Graduate de TotalEnergies à Houston figure dans le
catalogue. Sa description précise une clôture le 18 octobre 2026, un début le
1er octobre 2027 (éventuellement plus tôt) et des restrictions de visa. Ces
conditions restent dans le texte complet ; le score ne vaut pas confirmation
d’éligibilité et les rotations décrites comprennent plusieurs fonctions hors
front office. Les dates de cette formulation restent à structurer séparément.

Sources : [TotalEnergies Trading Careers](https://trading.totalenergies.com/en/careers/join-our-teams/),
[catalogue TotalEnergies](https://jobs.totalenergies.com/en_US/careers/SearchJobs),
[ENGIE](https://jobs.engie.com/), [sitemap ENGIE](https://jobs.engie.com/sitemap.xml),
[EDF Trading](https://www.edftrading.com/careers/job-opportunities).

## Validation et installation

Les trois collectes publiques ont réussi séparément : TotalEnergies, sept
fiches en 28 requêtes ; ENGIE, douze fiches distinctes en 37 requêtes ; EDF
Trading, cinq fiches en onze requêtes. Trois offres atteignent le seuil de 70.
Deux collectes supplémentaires sur une copie de la base réussissent, chacune
en **76 requêtes**. Résultat : **24 offres nouvelles**, **9 pertinentes**,
**3 au seuil d’alerte**, **24 dates de publication**, **5 fiches avec missions**
et **8 avec indications de diplôme**. Les **1 000 offres antérieures** gardent
leurs scores ; candidatures, historiques et alertes sont inchangés. Aucun
message de test envoyé et aucune alerte créée par ces deux imports.

Suite locale : **4 158 tests réussis, 4 ignorés**, dont 62 contrôles supplémentaires
sur les nouvelles sources et les dates. **11 tests JavaScript réussis**, lint
et format de 255 fichiers validés, analyse statique des 93 modules réussie.
Le paquet construit contient 98 fichiers applicatifs comparés aux sources.
Les contrôles après installation sont consignés ci-dessous une fois terminés.
