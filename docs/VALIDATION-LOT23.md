# Validation du lot 23 — Jump, expérience et mesure Workday

17 septembre 2026, Windows / Python 3.14.3. Trois sous-agents ont réalisé la mesure
Workday, l'audit d'expérience et la capture Jump. L'agent principal a comparé les
scores sur toute la base, validé les changements, répété l'import sur copie, puis
actualisé les données et le dashboard.

## Résultat métier

| Mesure | Avant | Après |
| --- | ---: | ---: |
| Offres conservées | 811 | 813 |
| Offres actives | 809 | 811 |
| Actives avec score ≥70 | 163 | 163 |
| Actives avec score ≥55 | 247 | 250 |
| Offres Jump conservées | 23 | 25 |

Le catalogue Jump a été relu à **00:56:12 UTC** : 108 annonces, réponse identique
octet pour octet au corpus du lot 12. Les deux ajouts proviennent de l'amélioration
du filtre du lot 21 : **Python Software Engineer (8104832), score 51**, et
**Quantitative Developer (7822791), score 53**. Ils ne constituent ni deux nouvelles
publications ni deux offres prioritaires ≥55.

Le catalogue validé par URL, horodatage, taille et SHA-256 a été intégré à
**00:57:52 UTC**, sans requête supplémentaire : **25 reçues, deux nouvelles,
quatre mises à jour, zéro fermeture, zéro alerte**. La collection reste partielle ;
une absence n'entraîne aucune fermeture. Les durées et requêtes de l'import décrivent
le rejeu local, tandis que `jump/capture.json` conserve les deux échanges réseau.
Voir [JUMP-REFRESH-LOT23.md](JUMP-REFRESH-LOT23.md).

## Correction des exigences d'expérience

La normalisation supprimait les tirets : `2-5+ years` pouvait donc devenir un
minimum de cinq ans. Les intervalles utilisent désormais leur borne inférieure
avant normalisation. Les motifs antérieurs de minimum explicite sont préservés.
Une préférence directement attachée à l'expérience est distinguée d'une obligation.
La phrase de track record de codage vérifiée chez Jump alimente le champ structuré
d'expérience uniquement dans la rubrique des compétences requises.

La revue globale a permis d'écarter une première version trop large avant toute
modification de base. Le correctif final change huit explications sur les 811
objets conservés : sept intervalles et une préférence directe. Après l'import Jump,
**sept fiches supplémentaires ont été recalculées**, sans modifier leurs dates
d'observation. Quatre scores finaux hors Jump changent :

| Offre | Avant → après |
| --- | --- |
| Citi — US Rates Strategist, Treasury Trading | 0 → 68 |
| Goldman Sachs — US Power Trading, Associate | 74 → 66 |
| UBS — Execution Trader, Asset Management | 0 → 70 |
| UBS — Prime Financing Relationship Manager | 0 → 57 |

Un minimum de trois ans conserve zéro point de compatibilité junior. Un score
élevé ne garantit donc pas l'éligibilité au poste. Les fonctions techniques Jump
sans preuve suffisante restent exclues. Détails et limites :
[EXPERIENCE-AUDIT-LOT23.md](EXPERIENCE-AUDIT-LOT23.md).

## Mesure Workday

Une fiche existante par banque a été lue deux fois : Barclays, Deutsche Bank,
Morgan Stanley et Citi. **12 requêtes réussies** au total, dont quatre robots et
huit détails. Les détails répondent `200`, sans `ETag` ni `Last-Modified`, avec
`no-store`, `Vary` et cookies. Aucun corps n'est stocké ou réutilisé ; aucun gain
de cache n'est démontré. L'option reste désactivée.

La mesure distingue corps décodé et corps téléchargé compressé. Elle ne constitue
pas une collecte complète et ne modifie pas la fraîcheur des sources en base.
Les premiers essais sans accès réseau ont échoué au transport ; ils sont conservés
séparément et ne sont pas présentés comme des réponses des serveurs.
Voir [WORKDAY-MEASURE-LOT23.md](WORKDAY-MEASURE-LOT23.md).

## Préservation et livraison

- Sauvegarde SQLite vérifiée avant intervention : `data/discovery/lot23/before-refresh.zip`.
- Répétition sur copie avec note de candidature synthétique : import puis second passage sans ajout, modification, fermeture ou alerte. La note est préservée ; elle n'a jamais été ajoutée à la base réelle.
- Sur la base réelle : candidatures existantes, historique de candidature, alertes, premières détections et observations des sources hors Jump préservés. Contrôles SQLite et relations valides.
- CSV et HTML régénérés, serveur local redémarré. Navigateur vérifié : 813 offres au total, 811 actives, filtre Jump à 25 résultats et détail Python Software Engineer à 51/100.
- Santé locale : **healthy**, **24 sources fraîches** au seuil de 24 heures lors du bilan. Cette fraîcheur ne signifie pas que toutes ont été collectées pendant ce lot.

Preuves locales : `before.json`, `backup.json`, `score-impact.json`, `rehearsal.json`,
`import.json`, `health.json`, `jump/` et `workday-cache/`, sous
`data/discovery/lot23/`. Ces fichiers sont ignorés par Git. Le dashboard reste un
instantané local, à régénérer après une modification.

## Vérification finale

- **1 260 tests réussis**, soit **90 supplémentaires** ; couverture Python **96 %**.
- 43 nouveaux cas d'expérience, 27 tests de mesure Workday et 20 tests de capture/rejeu Jump.
- Ruff : **120 fichiers** ; mypy : **49 modules applicatifs et deux scripts**, sans erreur.
- Paquet reconstruit hors réseau depuis le lock, installé sans mode éditable et testé.
- Une connexion SQLite non fermée dans une fixture de test a été corrigée ; les tests concernés passent avec les avertissements de ressources traités comme erreurs.

Aucune nouvelle dépendance, migration de schéma ou modification des références
`sources/`. Aucun watcher, message Telegram ou formulaire de candidature lancé.
Les accès Citadel/JPMorgan n'ont pas été retentés dans ce lot. La validation Docker,
la supervision prolongée et l'hébergement distant restent à réaliser séparément.
