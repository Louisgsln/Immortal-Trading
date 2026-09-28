# Lot 94 — ENGIE, Nomura et six nouveaux employeurs

Ce lot répond aux incidents du 28 septembre et étend le radar à **78 sources
pour 72 employeurs**. Les recherches restent partielles, avec premier import
silencieux et aucune fermeture déduite d'une absence.

## Fiabilité

**ENGIE** a supprimé trois champs de présentation : Business Unit, Division
et la répétition Legal Entity. Les douze fiches anglaises sélectionnées passent
de 18 à 15 blocs. Les deux formes sont désormais reconnues explicitement :
référence, titre, lien canonique, lien de candidature, date et limites de
description restent contrôlés. Un champ décalé ou une identité contradictoire
fait toujours échouer la collecte. Les douze pages réelles ont été rejouées.

La relecture du sitemap compare les liens du périmètre ciblé. Une modification
d'une annonce sans rapport avec le trading ne fait plus échouer ce périmètre.
Si les liens ciblés changent, un nouveau parcours complet est autorisé une
seule fois, dans le même budget de temps ; les deux résultats ne sont pas mélangés.

**Nomura Campus** avait réussi à 11:29 puis redemandé un CAPTCHA à 11:35.
Le fichier de session optionnel n'était pas configuré sur cette instance.
La consultation passe de cinq à **trente minutes** et les titres explicitement
stage, summer analyst, placement ou programme de découverte sont filtrés
avant l'accès aux détails. Les Graduate admissibles restent surveillés, y compris
les titres Analyst / Associate. Le blocage CAPTCHA et une session à renouveler
sont tous deux identifiés comme des restrictions d'accès dans l'état du radar.

Ce changement réduit les requêtes, sans garantir que Nomura renonce à ses
contrôles. La session du navigateur existant affichait encore le catalogue,
mais l'accès HTTP du scanner demandait une vérification. L'outil manuel de
renouvellement n'a pas enregistré de session dans son délai. Aucun CAPTCHA
n'est résolu automatiquement et aucune liste bloquée n'est assimilée à zéro offre.

## Extension vérifiée

| Employeur | Preuve officielle / catalogue | Fiches ajoutées sur copie |
| --- | --- | ---: |
| Headlands Technologies | [Carrières](https://www.headlandstech.com/careers/) → Greenhouse `headlandstechnologiesllc` | 2 |
| Radix Trading | [Page employeur](https://www.radixtrading.com/) → deux catalogues distincts `radixuniversity` et `radixexperienced` | 2 campus + 1 professionnel |
| 3Red Partners | [Carrières](https://www.3redpartners.com/careers/) et [catalogue employeur](https://job-boards.greenhouse.io/3redpartners) | 3 |
| Tudor Group | [Carrières](https://www.tudor.com/careers/) → Greenhouse `tudorgroup` | 2 |
| Acadian Asset Management | [Offres](https://www.acadian-asset.com/careers/open-positions) → intégration Greenhouse `acadianassetmanagementllc` | 1 |
| Arrowstreet Capital | [Carrières](https://www.arrowstreetcapital.com/professional-careers/) → [Workday](https://arrowstreetcapital.wd5.myworkdayjobs.com/en-US/Arrowstreet) | 1 |

Les sept portails sont vérifiés toutes les trente minutes. L'employeur,
l'identifiant, l'origine et le chemin des liens sont validés ; Acadian exige un
unique paramètre `gh_jid` correspondant exactement à la fiche. Les formulaires
génériques 3Red, les inscriptions au vivier Tudor, les intitulés de support,
stages et fonctions de stewardship restent hors du périmètre.

**12 nouvelles fiches**, toutes datées, dont **2 au seuil de 70** : Analyst,
Portfolio Construction & Trading chez Acadian (88), Graduate Trader chez
3Red (86). Les dix rôles quantitatifs restent à qualifier : leur titre seul
ne suffit pas à obtenir un score trading. Leurs descriptions complètes sont
conservées ; les extractions structurées de missions et diplômes ne sont pas
encore adaptées à ces nouvelles sources. Pas d'enrichissement IA ni de comparaison CV.

## Validation avant installation

Deux collectes publiques successives sur une copie de la base : **8 sources
réussies, 24 fiches reçues, 55 requêtes par passage**. Premier passage : 12 ajouts ;
second : aucun ajout ni changement. Aucun conflit, aucune lacune, aucune fermeture
et aucune alerte ajoutée. ENGIE retrouve ses 12 fiches sans en modifier le contenu.
Les scores des **1 163 offres préexistantes**, candidatures et historiques
sont préservés. Nomura est contrôlé séparément, pour conserver un diagnostic
explicite tant que le site bloque l'accès.

Les preuves de tests, installation et fonctionnement continu sont ajoutées
après leur vérification effective.
