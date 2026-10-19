# Fiabilité, employeurs et LinkedIn — lots 177 à 179

État de préparation du 19 octobre 2026. **Pas encore installé.** Le profil d’exploitation
reste à 122 sources / 110 employeurs. Le déploiement nécessite l’accès aux données et
à Docker ; le contrôle automatique a refusé la réouverture du blocage de sudo en
considérant l’autorisation précédente comme terminée. Une nouvelle autorisation
explicite a été demandée. Aucun contournement ni modification de production effectués.

Au contrôle HTTPS initial de 16:12 UTC : réponse 200 en 16,558 s, 1 983 fiches,
1 957 actives, radar actif avec signal vieux de quatre secondes, 105/122 sources à
jour. Les 17 incidents concernent les collectes, sans preuve d’arrêt du watcher.
Les services système remote, cloud et dashboard sont actifs. Les états Docker,
le curseur et les sauvegardes de production ne sont pas vérifiables sans cet accès.

## Lot 177 — régressions constatées

Nomura professionnels et HSBC campus gardent une offre pourvue dans leurs listes,
puis publient « Sorry, this position has been filled. » sur sa fiche. Le collecteur
continuait à attendre une fiche ouverte et interrompait toute la source. Le correctif
reconnaît uniquement ce message exact dans son conteneur de fiche, avec URL canonique
et référence employeur concordantes. Société Générale peut renvoyer HTTP 410 pour
une fiche encore listée ; ce statut explicite est isolé des autres erreurs d’accès.
Un CAPTCHA, une redirection, HTTP 403/404 ou la disparition d’une recherche partielle
ne constituent jamais une fermeture.

La fermeture porte sur une association exacte source/référence/URL. Les identifiants,
notes, candidatures, souhaits, alertes et historiques sont conservés. Une autre
association encore active garde l’offre canonique active. Le traitement est atomique,
idempotent, interdit pour une collecte contradictoire et journalisé avec sa preuve.
Le schéma SQLite reste en version 4.

HSBC professionnels publie des slugs français accentués : ils sont maintenant acceptés
sans relâcher les contrôles de domaine et de numéro de poste. Workday peut changer
pendant la pagination : un seul nouveau parcours propre est permis, sous le budget
initial, sans conserver les lignes ni lacunes du parcours abandonné. Les contrats
invalides et les refus d’accès ne sont pas réessayés par cette règle.

RBC a atteint 501 résultats, au-delà du plafond historique de 500. Le plafond borné
passe à 1 000, sans réduire ses sept recherches ou modifier les critères métier.
Bank of America renvoie une ligne ne contenant que la référence `26022615` : elle
reste une lacune visible ; les autres offres peuvent être collectées. Aucun titre
ou lien n’est reconstitué à partir de cette seule référence.

Les essais publics depuis le VPS, dans une copie de recherche sans accès aux données
ou à Telegram, réussissent sur Nomura professionnels (14 offres), HSBC campus (4),
HSBC professionnels (8), Société Générale (32), State Street (39), Barclays (23),
Morgan Stanley (10), Citi campus (15), TD (3), BMO (38) et U.S. Bank (19).
Ces résultats ne sont pas présentés comme des succès de production. BNP et les
portails protégés restent ouverts au carnet ; Nomura campus attend l’intervention
humaine précédemment laissée en attente par le propriétaire.

## Lot 178 — six employeurs

| Employeur | Catalogue officiel vérifié | Offres retenues à la première lecture |
|---|---|---:|
| Lloyds Banking Group | Workday `lbg/LBG_Careers` | 4 |
| Lombard Odier | Workday `lombardodier/Lombard_Odier_Careers` | 4 |
| Janus Henderson | SuccessFactors `jobs.janushenderson.com` | 4 |
| Belvedere Trading | Lever `belvederetrading` | 7 |
| Tibra Capital | Workable `tibra-capital-1` | 0 |
| Eclipse Trading | Greenhouse `eclipsetrading` | 8 |

27 fiches au premier contrôle, sans garantie de volume hebdomadaire. Chaque plateforme
est reliée par une page officielle de l’employeur ; ses identités, totaux et fiches
complètes sont contrôlés. Tibra déclare explicitement zéro poste public. Ce constat
ne ferme aucune ancienne offre. Les titres Summer et les viviers sont exclus ;
les offres off-cycle/longues sont conservées, y compris sans conditions connues.
Les rôles seniors restent examinables dans le flux tous scores. Les qualifications
et points de score ne sont pas augmentés au nom d’une banque ou d’un fonds.

Le profil préparé atteint **128 sources / 116 employeurs**. Ces chiffres ne doivent
être annoncés dans `/statuts`, `/sources` et le Dashboard qu’après installation.
LinkedIn manuel n’est pas ajouté à ces compteurs. Le premier import des six sources
doit rester silencieux et être mesuré sur une sauvegarde restaurée avant déploiement.

## Lot 179 — import LinkedIn privé

Voir le [mode d’emploi et les limites](LINKEDIN.md). Aucune connexion LinkedIn ou
Gmail n’est configurée. Les messages sont acceptés uniquement du propriétaire dans
le chat privé autorisé, avec le contrôle de date et de destinataire du bot déjà en
place. La déduplication préserve le suivi et n’actualise jamais une fiche officielle
à partir d’une annonce copiée. La mention d’import manuel apparaît aussi sur mobile.

## Validation et suite d’installation

Les groupes ciblés passent, ainsi que 34 tests JavaScript, Ruff, Mypy sur 133 modules
et le contrat de 89 contrôles du Dashboard. La suite Python complète et la CI de
ce changement sont en cours ; les résultats définitifs seront inscrits dans les preuves.

Une sauvegarde vérifiée de production, la simulation sur copie, la construction
Docker, l’installation et les quinze contrôles de conservation restent à faire
après autorisation. Le lien HTTPS privé, les alertes tous scores, le digest 09:00
et les points d’état 13:00/18:00 Paris doivent être conservés. Aucun message Telegram
de test n’a été envoyé pendant cette préparation.

[Carnet](TASK-BOARD.md) · [Sources](RADAR-SOURCES-LOT178.md).
