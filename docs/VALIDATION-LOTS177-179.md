# Fiabilité, employeurs et LinkedIn — lots 177 à 179 installés

Installés sur OVH le 19 octobre 2026 à 19:14 UTC. Au relevé du **19/10/2026 à 19:23 UTC** : **128 sources / 116 employeurs**, **121 à jour et 7 à surveiller**. Radar et Dashboard sains, écouteur Telegram et sauvegardes actifs, redémarrage automatique conservé. Le contrôle de santé du nouveau radar réussit en 7.022 secondes ; l’ancienne image dépassait son délai de 30 secondes alors que le watcher collectait encore.

Le site privé répond en HTTP 200, sans identifiant ni mot de passe, en 14.012 secondes au dernier contrôle. Le premier accès après remplacement prenait 26,584 secondes, puis 17,510 secondes. Le premier affichage reste au carnet, lot 176 ; aucun objectif de cinq secondes n’est déclaré atteint.

## Lot 177 — reprise des collectes

Nomura professionnels et HSBC campus distinguent une offre explicitement pourvue d’une erreur d’accès. Le message employeur exact, son conteneur de fiche, la référence et l’URL canonique doivent concorder. Société Générale isole HTTP 410 sur une fiche identifiée. Les refus 403/404, CAPTCHA, redirections et absences d’une recherche partielle ne ferment aucune offre.

Une fermeture désactive seulement l’association source/référence/URL exacte. Une autre association active garde l’offre ouverte. Les identifiants et historiques restent conservés ; le traitement est atomique et idempotent, sans migration du schéma SQLite 4. HSBC professionnels accepte ses slugs accentués avec les mêmes contrôles de domaine et de référence.

Workday autorise un seul nouveau parcours propre si la pagination change, sous son budget initial. Un format invalide ou un refus d’accès ne bénéficie pas de cette reprise. Le plafond RBC passe de 500 à 1 000, sans supprimer de recherche. Les lignes opaques observées Bank of America et Citi sont traitées comme des lacunes, sans inventer de titre ou de lien. Citi accepte ses références observées à huit ou neuf chiffres ; la levée d’une lacune exige une preuve publique contrôlée.

Avec l’image construite, 17 collecteurs sont revalidés en direct, puis rejoués sans transport Telegram sur une sauvegarde restaurée. L’import mesuré ajoute **33 fiches**, ne modifie aucun suivi, et ferme **deux offres explicitement pourvues**. Six nouvelles alertes sont mises en file selon la politique normale ; les 27 fiches des nouveaux employeurs constituent une référence initiale silencieuse. State Street a été isolé de cet import après réponse invalide, puis traité au [lot 180](VALIDATION-LOT180.md).

## Lot 178 — six employeurs installés

| Employeur | Source | Fiches initiales |
|---|---|---:|
| Lloyds Banking Group | lloyds | 4 |
| Lombard Odier | lombard_odier | 4 |
| Janus Henderson | janus_henderson | 4 |
| Belvedere Trading | belvedere | 7 |
| Tibra Capital | tibra | 0 |
| Eclipse Trading | eclipse | 8 |

Les deux lectures publiques de préparation concordent : 167 résultats examinés et 27 fiches retenues, dont dix à score ≥ 70 et dix-sept à zéro. Une troisième collecte dans l’image construite, entre 19:00 et 19:01 UTC, confirme ces volumes avant simulation et import. Les six sources sont à jour au relevé final. Tibra publie explicitement zéro ouverture ; aucune fiche détaillée n’a donc pu être vérifiée.

Les stages off-cycle et longs 2027 restent inclus, avec les métiers et lieux existants. Les titres Summer et viviers restent exclus ; les durées et années absentes ne sont jamais déduites du nom de l’employeur. Les scores ne sont pas augmentés artificiellement. [Inventaire complet](RADAR-SOURCES-LOT178.md).

## Lot 179 — LinkedIn dans le suivi privé

La commande **/linkedin** importe le texte et le lien d’une annonce copiée par le propriétaire. La fiche rejoint le Dashboard et les boutons Souhaits/Postulé utilisent le suivi partagé. Déduplication, contrôles de destinataire et de date, curseur persistant avant traitement et absence de rejeu sont testés. Une copie LinkedIn ne rafraîchit pas une vérification employeur ; son association inactive ne maintient pas ouverte une offre ensuite fermée officiellement.

La collecte automatique LinkedIn reste indisponible : ses chemins publics refusent la collecte via robots.txt. Aucun accès Gmail, session LinkedIn ou contournement n’est utilisé. LinkedIn manuel ne compte pas comme source surveillée. [Mode d’emploi](LINKEDIN.md).

## Conservation et validation

Sauvegarde de production format 2 vérifiée et restaurée sur une copie isolée. Le second import des six employeurs sur cette copie n’ajoute aucun doublon. Après déploiement, les **quinze contrôles de conservation passent** : inode et identifiants, candidatures et notes, souhaits, alertes envoyées, historiques, liaison et curseur Telegram, préférences du récapitulatif et liaison des messages d’état. Aucun rétablissement d’une ancienne base ; le Git HEAD de production et ses autres modifications sont conservés.

La [CI de validation](https://github.com/Louisgsln/Immortal-Trading/actions/runs/39293731137) réussit ses six jobs : **5 743 tests sur chacune des versions Python 3.11 à 3.14**, 34 tests JavaScript, Ruff, Mypy sur 133 modules et Docker. Sur le VPS, l’image non privilégiée passe les 89 contrôles du Dashboard et le parcours synthétique sauvegarde/restauration avec onze tables identiques. Le [complément State Street](VALIDATION-LOT180.md) possède sa validation distincte.

Le flux automatique de chaque nouvelle offre, même à zéro, reste activé. Les journaux confirment les deux messages d’état du 19 octobre à 13:00 et 18:00 Paris ; récapitulatif 09:00 conservé. Aucun message Telegram de test manuel envoyé pendant l’intervention.

L’autorisation temporaire sudo donnée pour cette intervention a été utilisée, puis la liste originale de 33 commandes bloquées a été rétablie et vérifiée. [Preuves](DELIVERY-LOTS177-179.json) · [Carnet](TASK-BOARD.md).
