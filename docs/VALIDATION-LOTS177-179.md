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
ou lien n’est reconstitué à partir de cette seule référence. Citi publie également la référence masquée
`261001222`, à neuf chiffres : son format ne bloque plus le catalogue. La lacune
n’est résolue que si la recherche exacte fournit une preuve publique de catégorie
hors du périmètre, selon les contrôles déjà en place ; aucune fermeture déduite.

Les essais publics depuis le VPS, dans une copie de recherche sans accès aux données
ou à Telegram, réussissent sur Nomura professionnels (14 offres), HSBC campus (4),
HSBC professionnels (8), Société Générale (32), State Street (39), Barclays (23),
Morgan Stanley (10), Citi campus (15), TD (3), BMO (38), U.S. Bank (19), RBC (9), Citi professionnels (38) et Scotiabank (11).
Bank of America récupère 9 offres, avec la référence opaque toujours signalée.
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

Deux collectes concordantes : **27 fiches**, dont dix à score ≥ 70 et dix-sept à zéro,
pour 167 résultats examinés dédupliqués par source. Un score ne confirme pas les
conditions d’un stage ni l’éligibilité du candidat. Les profils publiés, identités,
descriptions et conditions sont identiques entre les deux lectures ;
[preuves publiques](SOURCE-AUDIT-LOT178.json). Aucune garantie de volume hebdomadaire. Chaque plateforme
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
et le contrat de 89 contrôles du Dashboard. La suite Python complète a relevé une
assertion historique imposant encore 500 résultats chez RBC ; elle est actualisée
à 1 000 pour cette source uniquement, et son groupe de 108 cas réussit. Les
[commits de préparation](https://github.com/Louisgsln/Immortal-Trading/tree/43fd126893db6df1fe6cf058aba8cc6e313d0f33)
et la [CI finale](https://github.com/Louisgsln/Immortal-Trading/actions/runs/39293731137)
restent distincts du déploiement. La CI Python 3.14 réussit les **5 743 tests**, sans échec ni test ignoré ; JavaScript est vert. Les autres versions et le contrôle conteneur hébergé sont encore en cours.

Le paquet wheel est construit depuis le checkout public exact `43fd126` et testé
par son installation non éditable sous l’utilisateur Ubuntu : contrat Dashboard et
parcours synthétique sauvegarde/vérification/restauration réussis. L’exercice local
indépendant réussit aussi : huit offres, onze tables identiques après restauration.
Pour Tibra, aucune fiche détaillée n’est actuellement publiée : le contrôle réel
porte sur la déclaration et le catalogue vide.

Ces contrôles ne constituent pas une sauvegarde ni une validation Docker de production.

Une sauvegarde vérifiée de production, la simulation sur copie, la construction
Docker, l’installation et les quinze contrôles de conservation restent à faire
après autorisation. Le lien HTTPS privé, les alertes tous scores, le digest 09:00
et les points d’état 13:00/18:00 Paris doivent être conservés. Aucun message Telegram
de test n’a été envoyé pendant cette préparation.

[Carnet](TASK-BOARD.md) · [Sources et inventaire installé](RADAR-SOURCES-LOT178.md).

Le manifeste des 19 fichiers de code et de profil est vérifié en lecture seule :
versions anciennes et paquet cible concordants. Aucun checkout/reset de production.
Le nouveau cas de passage LinkedIn manuel → source officielle conserve le suivi
et permet une fermeture employeur ultérieure ; 81 tests associés réussissent.

Contrôle de production du 19 octobre à 17:26 UTC : HTTPS 200 en 14,796 secondes,
radar actif, **110/122 sources à jour**, 110 employeurs, alertes tous scores activées.
[Inventaire complet daté](RADAR-INVENTORY-20261019.json). Les six ajouts restent non installés.

Le parcours complet local a exécuté 5 737 cas : 5 736 réussis, une ancienne fixture
du probe assimilant une page courte à un format invalide. Elle est remplacée par
un conteneur réellement invalide, et un cas distinct vérifie que la page courte
réessaie seulement la même recherche une fois, sans autre requête ni détail.
Les 83 cas probe/reprise/snapshot réussissent après correction ; les huit variantes du contrôle corrigé sont revérifiées après la fin du parcours complet. La CI finale porte
sur 5 743 cas, dont 96 nouveaux, et distingue les quatre versions Python. Python 3.14 les réussit tous.
Avant toute installation, les six catalogues seront relus après construction de
l’image ; une capture ancienne ne doit pas être importée comme une vérification actuelle.
