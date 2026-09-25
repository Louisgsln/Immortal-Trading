# Collecte BNP avec références conflictuelles

Lorsque plusieurs URL BNP portent le même identifiant employeur, le collecteur
compare les fiches complètes. Des alias identiques conservent une URL stable.
Depuis le lot 56, un désaccord déclenche d'abord une vérification bornée de la
fiche de recrutement officielle, seulement si toutes les variantes y pointent
avec la même identité. Une seule variante doit correspondre à son titre et sa
description complète, avec référence employeur et URL canonique concordantes.
Sinon, toutes les variantes restent exclues du résultat, indépendamment de leur ordre. Une troisième variante
identique à la première ne réintroduit pas la référence.

Les autres références sont importées seulement après lecture et validation de
toutes les pages prévues. Une erreur HTTP, une pagination incohérente, un budget
dépassé ou une fiche invalide rejette toujours la collecte entière.

## État et protections

- Une collecte avec conflits n'est jamais un succès : elle incrémente le compteur
  d'échecs, conserve la dernière date de succès et utilise la temporisation existante.
- Les anciennes fiches conflictuelles gardent leurs données et dates de collecte.
  Aucune fermeture n'est déduite des exclusions ou de l'absence d'une annonce.
- Aucun événement d'alerte n'est créé pour les imports de ce scan dégradé. Les
  alertes en attente et rappels de la source sont suspendus jusqu'à un succès
  ultérieur. Les autres sources continuent normalement.
- Une première collecte dégradée ne termine pas l'initialisation silencieuse.
- Une collecte ultérieure sans conflit résout le diagnostic. Elle suit ensuite
  les règles ordinaires de déduplication, d'initialisation et de notification :
  les offres déjà importées ne génèrent pas rétroactivement une alerte de nouveauté.

## Diagnostic et aperçu

`trading-radar scan --dry-run --source bnp` produit un aperçu `incomplete` avec
les changements simulés et `metrics.degraded.bnp` : identifiants exclus, URL des
alias et noms des champs divergents. Aucune valeur de description n'est copiée
dans le diagnostic. Un aperçu ne modifie pas la base réelle.

Les conflits sont conservés dans le journal existant `scan_runs`, sans migration
de la base. `health`, l'audit des sources et les données du dashboard exposent
`collection_conflicts`. Dans **Santé des sources**, ouvrir **Collecte dégradée**
pour examiner les références et leurs variantes. Le dernier scan avec conflits est présenté comme une collecte partielle avec
références contradictoires, même sans succès complet antérieur. Un échec réseau
ultérieur reste signalé séparément ; la source n'est pas comptée comme à jour.

Une collecte d'une autre source ou un échec réseau ultérieur ne supprime pas les
preuves du dernier conflit non résolu. Le diagnostic est historique : il ne
prétend pas que les pages ont été relues lors d'un échec réseau.

## Périmètre de validation

Les tests reproduisent des divergences de description, de date et de contrat,
des alias multiples et un incident HTTP après détection d'un conflit. Ils
contrôlent aussi les transactions, les notifications, la reprise, la consultation
du diagnostic et l'aperçu sans écriture.

Le lot est désormais installé dans l'instance Windows isolée et intégré à `main`
avec le lot 50. Les collectes publiques ont repris. Un nouveau conflit ou incident
d'accès reste signalé ; l'installation ne garantit pas la disponibilité du portail.

Le [lot 56](VALIDATION-LOT56.md) résout les deux conflits observés grâce aux
fiches officielles partagées et permet une collecte de 31 offres. Les protections
ci-dessus continuent de s’appliquer aux autres conflits.
