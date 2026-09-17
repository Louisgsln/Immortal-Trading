# Cache conditionnel des détails Workday

Ce cache optionnel réduit les octets transférés lorsque le serveur Workday fournit
des validateurs HTTP. Il conserve les réponses JSON uniquement dans la mémoire du
processus `watch`. Chaque fiche est toujours vérifiée auprès du serveur : une réponse
`304 Not Modified` permet de réutiliser le corps précédemment reçu. Le nombre de
requêtes ne diminue pas et aucun gain n'est garanti si le serveur ne fournit pas de
validateur.

## Activation

Dans les `options` d'une source Workday, ajouter :

```yaml
conditional_details: true
```

La valeur par défaut est `false`. L'option appartient exclusivement aux sources
Workday et n'est pas acceptée par les options génériques des autres collecteurs.
La configuration de production n'est pas modifiée par cette livraison.

Le watcher partage un `JSONCache` entre les scans mais crée un nouveau client HTTP
à chaque scan. Les règles `robots.txt` sont donc relues à chaque passage. Un scan
ponctuel sans cache injecté garde le comportement habituel, y compris lorsque
l'option est présente. Redémarrer le watcher vide le cache.

## Garanties

- Les recherches POST, la pagination et les limites de collecte restent inchangées.
- Clé : identifiant de source et URL exacte du détail.
- Un `200` JSON valide avec `ETag` ou `Last-Modified` remplace le corps et ses
  validateurs. Les deux en-têtes conditionnels sont envoyés lorsqu'ils existent.
- Une réponse `304` n'est utilisable qu'avec une entrée encore présente et non
  expirée, et des métadonnées compatibles. Un `304` inattendu fait échouer la
  collecte ; il ne transforme pas une réponse vide en fiche valide.
- Les accès restent soumis à robots, au délai de requêtes et au `Crawl-delay`,
  même lorsque le corps est déjà en mémoire.
- Les erreurs réseau, refus robots, redirections, `403`, `404` ou erreurs serveur
  font échouer la collecte et suppriment l'entrée concernée. Aucun contenu périmé
  n'est fourni comme solution de secours.
- Les réponses `Cache-Control: no-store` ou `private`, `Vary` et `Set-Cookie` ne
  sont pas conservées. Les requêtes avec autorisation, cookies ou `no-store`
  contournent le cache. `no-cache` reste compatible : il impose déjà la
  revalidation faite systématiquement.
- Limites : 256 entrées, 1 Mio de corps par entrée, 16 Mio de corps au total ;
  les URL, identifiants de source et validateurs ont aussi des limites de taille.
  Les entrées les moins récemment utilisées sont évincées si nécessaire.
- Durée maximale de résidence : une heure depuis le dernier `200`. Un `304` ne
  prolonge pas cette durée. Les entrées expirées sont purgées à l'accès suivant.
- Aucun fichier cache, aucune nouvelle table SQLite et aucun envoi de message.

Le cache retourne un objet JSON nouvellement décodé à chaque lecture ; modifier une
fiche en mémoire ne modifie pas le corps utilisé au passage suivant. La validation
Workday habituelle s'applique aussi aux corps revalidés. Les inventaires de recherche
restent partiels et ne déclenchent pas de fermeture par absence.

## Vérification locale

```powershell
.venv/Scripts/python.exe -m pytest tests/test_http_cache.py tests/test_workday_cache.py tests/test_http_policy.py tests/test_workday.py
```

Ces tests utilisent un transport HTTP simulé : validateurs, remplacement `200`,
`304`, isolation des sources, expiration, éviction, erreurs, règles robots,
cadencement et collectes Workday successives. Ils ne démontrent pas que les
endpoints de production fournissent actuellement des validateurs.

## Mesure réelle du lot 23

Deux lectures de chacune de quatre fiches Workday ont été effectuées le 17 septembre
2026. Les huit réponses étaient des `200`, sans validateur et avec `no-store` :
aucune réponse stockée ou réutilisée. Le cache reste désactivé dans la configuration.
Le [rapport de mesure](WORKDAY-MEASURE-LOT23.md) détaille les octets reçus, le périmètre
et le script reproductible. Ce résultat ne généralise pas le comportement de quatre
fiches à toutes les réponses futures.
