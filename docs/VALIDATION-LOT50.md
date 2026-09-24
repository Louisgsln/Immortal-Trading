# Lot 50 — Alertes Telegram et confirmation de candidature

Validation locale du 25 septembre 2026.

## Résultat

Les alertes individuelles affichent une carte HTML compacte et deux boutons :
ouverture du lien employeur et confirmation **J’ai postulé**. Une confirmation
met à jour le suivi local, sa date et son historique. Le dashboard modifiable
relit le suivi toutes les dix secondes quand la page est visible.

## Vérifications

- Suite complète Windows : **2 927 tests réussis, 4 ignorés** (liens symboliques
  indisponibles dans l’environnement de test).
- Ruff, formatage et mypy : contrôles réussis.
- 30 tests dédiés : échappement HTML et longueur, URL non sûres, signatures liées
  au bot/chat, expéditeurs non autorisés, clics répétés, échec de confirmation,
  contention SQLite, retour arrière atomique et sauvegarde du curseur.
- Test HTTP du dashboard : accès authentifié et nouvelle valeur visible dès
  la confirmation, sans reconstruction de la page complète.
- Vérification dans le navigateur avec une base synthétique distincte : un clic
  Telegram simulé fait apparaître **Postulé** et le compteur passe de 0 à 1,
  sans rechargement. Une modification externe pendant la saisie conserve la note
  et désactive la sauvegarde jusqu’à relecture.
- Construction du paquet installable réussie.

## Limites explicites

Le bouton d’ouverture ne remplit ni ne transmet de candidature. La confirmation
est une déclaration de l’utilisateur. Les étapes ultérieures ne sont jamais
rétrogradées ; les notes, contacts, actions et dates existantes sont préservés.
Les anciens messages et les listes de commandes ne sont pas réécrits.
Les exports HTML restent des instantanés. Le PC et le service Telegram doivent
fonctionner pour traiter les clics ; le dashboard local doit être rechargé une
fois après une mise à jour du serveur.

La confirmation utilise une transaction SQLite `BEGIN IMMEDIATE` indépendante
du verrou de collecte réseau. Le scanner conserve les lignes de candidature
existantes (`INSERT OR IGNORE`). Le statut et l’historique sont validés ensemble,
et une base occupée produit un message de réessai plutôt qu’un faux succès.
