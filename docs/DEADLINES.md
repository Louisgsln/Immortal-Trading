# Échéances et rappels

## Consulter sans envoyer

Depuis la racine, utiliser `trading-radar` ou `.\.venv\Scripts\trading-radar.exe` :

```powershell
trading-radar deadlines list
trading-radar deadlines list --days 30 --min-score 70
trading-radar deadlines list --include-expired
trading-radar deadlines reminders
```

`list` affiche les échéances connues dans les 90 prochains jours par défaut, ainsi que les contradictions à vérifier. `--include-expired` inclut aussi les dates passées. Une date avec heure est comparée à l'instant actuel ; une date sans heure est comparée au jour courant UTC. L'affichage conserve le jour indiqué par la source et affiche séparément le timestamp UTC quand il est connu. Les conflits restent visibles indépendamment de l'horizon choisi.

`reminders` est toujours une **simulation**, même si les alertes sont activées. Il indique la fenêtre actuelle, l'éligibilité, le motif de suppression et l'état d'un éventuel envoi antérieur. Ces commandes n'utilisent ni réseau ni Telegram et ne mettent aucune alerte en file. Elles acceptent `--config-dir` et `--demo` comme le suivi de candidature.

Pour conserver un rapport sous PowerShell :

```powershell
trading-radar deadlines reminders | Out-File data/reminders.json -Encoding utf8
```

## Niveau de précision

| Valeur | Sens | Rappel possible |
| --- | --- | --- |
| `instant` | Date, heure et fuseau explicites, ou champ structuré déjà validé par le connecteur | Oui, sous conditions |
| `date` | Jour et année connus, mais heure ou fuseau insuffisants | Non |
| `conflict` | Dates contradictoires, jour de semaine incohérent ou instant invalide | Non |
| `unknown` | Aucun format fiable reconnu | Non ; absent de la liste détaillée |

L'extraction textuelle prend en charge les libellés anglais Application Deadline, Applications Close et Closing Date, avec année explicite. Elle accepte les dates ISO ou avec mois anglais écrit en entier, ainsi que les heures 24 h ou am/pm. Fuseaux pris en charge : UTC, GMT, HKT, SGT, CET, CEST et offsets numériques explicites `+08:00` ou `-04:00`. Ils sont interprétés tels qu'écrits, sans déduire un fuseau du lieu du poste. Les formes ambiguës comme CST ou UTC+08:00 restent sans instant précis dans ce lot.

Une année de programme ne fournit pas l'année d'une deadline. Une date de début, une recommandation d'appliquer tôt, une date relative ou un champ technique `validThrough` non validé ne deviennent pas une échéance. Plusieurs dates ou fuseaux contradictoires bloquent le rappel. Un champ structuré sans fuseau n'est plus artificiellement converti en UTC lors de la normalisation.

La consultation combine les champs structurés déjà stockés et les preuves présentes dans la description conservée. L'extraction textuelle est calculée à la lecture : elle ne modifie ni `last_seen`, ni score, ni offre, ni historique de candidature. Le champ deadline du CSV et de `applications show` reste celui fourni par le connecteur ; les preuves textuelles supplémentaires sont consultables via `deadlines`. Ce lot ne remplace pas les règles de normalisation de chaque portail.

## Fenêtres de rappel

| Temps restant jusqu'à l'instant exact | Rappel préparé |
| --- | --- |
| Plus de 7 jours | Aucun |
| Plus de 3 jours, jusqu'à 7 jours inclus | J−7 |
| Plus de 1 jour, jusqu'à 3 jours inclus | J−3 |
| Strictement positif, jusqu'à 1 jour inclus | J−1 |
| Échéance atteinte ou dépassée | Aucun |

Un passage prépare seulement la fenêtre actuelle. Après une interruption, les trois rappels ne sont pas envoyés ensemble. Le titre du message précise qu'il s'agit d'une fenêtre ; J−7 peut donc être envoyé quatre jours avant la deadline si c'est le premier passage dans cette fenêtre.

Le rappel exige aussi :

- Une offre active, un score au moins égal à `alert_min_score` (70 actuellement), un instant fiable et futur.
- Un statut `New`, `Reviewing` ou `To Apply`, sans date de candidature déjà renseignée. Applied, Rejected et toutes les étapes avancées ou fermées excluent le rappel.
- Une dernière observation datant d'au plus 24 heures par défaut ; un horodatage futur est rejeté. Une deadline proche ne rafraîchit pas une ancienne offre.

## Activation distincte

**Aucun rappel n'est activé actuellement.** Pour une future utilisation, les deux réglages doivent être vrais : `ALERTS_ENABLED=true` et `deadline_reminders_enabled: true` dans `config/settings.yaml`. Telegram doit également être configuré. Le délai de fraîcheur `deadline_reminder_max_age_hours` vaut 24 ; il est configurable entre une valeur strictement positive et 168 heures.

L'envoi s'exécute lors des commandes `scan` ou des passages du watcher déjà existant. Aucun service, tâche planifiée ou watcher n'est créé par ce lot. La référence initiale silencieuse de chaque nouvelle source reste sans rappel. Le mode démo désactive les deux types d'alertes.

La configuration générale des alertes conserve son effet sur les notifications d'offres nouvelles et modifiées. Les exclusions de candidature décrites ici portent sur les **rappels de deadline** ; elles ne changent pas les alertes générales.

## Fiabilité des envois

La clé d'un rappel associe l'identifiant de l'offre, la fenêtre et l'instant UTC de deadline. Une contrainte d'unicité empêche les doublons. Une nouvelle deadline reçoit sa propre clé ; avant d'envoyer une ancienne alerte en attente, le moteur relit l'offre et le suivi. Une date modifiée, supprimée, expirée ou devenue ambiguë, une fenêtre dépassée ou une candidature avancée supprime cet ancien rappel.

Les états `sent`, `unknown`, `sending` et `suppressed` ne sont pas rejoués automatiquement pour cette même clé. Un échec explicitement rejeté peut être retenté tant que l'éligibilité reste valable. Le marquage `sending` précède l'appel réseau : après un arrêt ou un timeout au résultat incertain, le radar ne renvoie pas aveuglément le message. Depuis le lot 18, une [décision opérateur explicite](ALERTS.md) permet de résoudre unknown/sending ; les contrôles d'éligibilité restent appliqués après remise en attente.

Désactiver les rappels suspend leur livraison ; une réactivation les soumet à nouveau aux contrôles, sans rejouer les fenêtres passées. Le verrou commun aux scans et à l'édition de candidature empêche qu'une commande locale modifie le suivi pendant une livraison.
