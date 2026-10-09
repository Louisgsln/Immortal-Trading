# Dashboard privé et radar permanent

Le radar, l’écouteur Telegram et les sauvegardes tournent sur le VPS, même
quand le poste de développement est fermé. Docker reprend les conteneurs après
un arrêt imprévu ou un redémarrage du serveur. Le Dashboard utilise un service
distinct et ne lance aucune collecte ni aucun envoi Telegram.

Le mode déployé `dashboard serve --private-editor` relit une observation SQLite
à chaque chargement de page. L’analyse des descriptions est réutilisée lorsqu’elles
restent identiques ; les modifications d’offres et de suivi restent visibles.
Le bouton **Actualiser** relit les offres, le suivi
et l’état des sources. Le suivi des candidatures se modifie dans les fiches :
statuts, notes, contacts, dates et prochaines actions. Une révision protège les
modifications entre appareils ; chaque changement est historisé. Les exports
HTML et le serveur local par défaut restent des instantanés en lecture seule.

Le Dashboard s’ouvre avec un lien HTTPS privé à enregistrer en favori, sans
saisie d’identifiant ou de mot de passe. Ce lien contient une clé aléatoire
de 256 bits ; toute personne qui reçoit le lien peut consulter la page et modifier
le suivi. Le lien actuel est conservé.
La racine `https://vps-b7a073e2.vps.ovh.net/` et les clés incorrectes renvoient
une erreur 404. Le lien complet est conservé dans un fichier privé hors du dépôt.
Le certificat HTTPS est délivré et renouvelé automatiquement par Let’s Encrypt.
Le service Caddy conserve les certificats dans `/srv/immortal-trading/web/caddy-data`;
ce dossier reste privé. Le navigateur ne transmet aucun référent aux liens externes.

`compose.dashboard.yaml` est indépendant de `compose.cloud.yaml`. Le premier
contient le Dashboard et l’accès HTTPS; le second conserve les trois rôles du
radar. Les deux déploiements lisent la même base existante, sans restauration
ni création d’une nouvelle base. Le Dashboard dispose du volume nécessaire aux
transactions du suivi, limitées dans l'application aux tables de candidatures
et à leur historique. Sa racine et sa configuration restent en lecture seule ;
ce conteneur ne reçoit aucun identifiant Telegram.

La passerelle HTTPS écoute sur les ports 80 et 443. Le port 80 redirige vers
HTTPS et permet la validation du certificat. Le Dashboard écoute uniquement
sur `127.0.0.1:8765`. Caddy transmet seulement les chemins du lien privé
au Dashboard; les fichiers, la base et les variables d’environnement ne sont
jamais servis comme un répertoire. Seules les routes de consultation et de suivi
sont autorisées sous le chemin privé. Caddy injecte un secret de passerelle.
Les écritures exigent une session de 24 heures, un cookie Secure/HttpOnly/
SameSite=Strict, un jeton CSRF et l'origine HTTPS exacte.

Les deux unités systemd démarrent les projets Compose au démarrage
du VPS, sans reconstruire les images et sans recréer les conteneurs existants.
Les collectes ne dépendent pas de la consultation du Dashboard. Les incidents
de source, notamment un HTTP 403 ou un CAPTCHA, restent visibles dans la page
**Santé des sources** et ne provoquent pas un redémarrage répété du radar.

Les paramètres web privés sont dans `.env.dashboard` et `.env.dashboard-editor`;
les réglages et les
identifiants Telegram existants restent dans `.env.cloud`. Le lien généré
est conservé hors du dépôt dans le dossier privé de publication
pour remise au propriétaire. Les rapports publics ne contiennent pas la clé du lien.

Avant publication : tests du mode direct, essai Docker sur données synthétiques,
validation de Caddy, accès refusé sans le lien, consultation directe avec celui-ci,
refus des écritures non autorisées, sauvegarde et vérification de l’état existant. Après
publication : contrôle du certificat public, test du lien privé et des chemins refusés,
lecture de données à jour et vérification des reprises automatiques. Les essais
d'écriture utilisent exclusivement une base synthétique ; les contrôles en
production lisent le suivi et soumettent seulement des requêtes invalides sans
modification de données.

Les cartes sur téléphone et l'onglet **Échéances** présentent les prochaines
actions et les dates limites par semaine, mois ou retard. Les filtres **Pays**,
**Durée** et **Début** gardent les informations inconnues distinctes. Voir les
validations des [lots 111](VALIDATION-LOT111.md), [112](VALIDATION-LOT112.md) et
[113](VALIDATION-LOT113.md).

Les lots [114](VALIDATION-LOT114.md), [115](VALIDATION-LOT115.md) et
[116](VALIDATION-LOT116.md) ajoutent les cartes de couverture des stages,
les filtres de consultation mémorisés et l'export calendrier. Dans Offres,
cochez « Retenir mes filtres sur cet appareil » pour retrouver votre sélection.
Les filtres des Candidatures sont conservés séparément ; décocher oublie ces
préférences sur l'appareil. Dans Échéances, choisissez la période puis utilisez
« Exporter le calendrier (.ics) ». C'est un import ponctuel, sans synchronisation
ni rappel automatique. Les heures précises annoncées sont affichées à Paris et
conservées dans le fichier. Les notes et contacts ne sont pas exportés.


## État des alertes affiché dans le Dashboard

Le Dashboard garde ses propres notifications et son contrôle Telegram désactivés et ne reçoit aucun secret du bot. `DASHBOARD_RADAR_ALERTS_ENABLED` est seulement l’indicateur non secret de l’état global des alertes dans le service radar. Le déploiement le lit dans ce service et l’écrit dans `.env.dashboard` ; l’audit compare l’état affiché au réglage effectif du radar. En cas de modification manuelle des alertes dans le radar, actualiser aussi cet indicateur et renouveler le seul conteneur Dashboard. Les critères affichés ne confirment jamais un envoi.
