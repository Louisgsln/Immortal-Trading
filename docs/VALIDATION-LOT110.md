# Lot 110 — Stages off-cycle et longs

Déployé le 6 octobre 2026 sur `vps-b7a073e2.vps.ovh.net`, image
`immortal-trading:lot110.1-internships-20261006` pour le radar, Telegram, les
sauvegardes et le Dashboard. Caddy et le lien HTTPS privé sont conservés.

## Comportement livré

Le Dashboard propose le filtre **Programme** : off-cycle, stages longs de
6–12 mois, stages de format inconnu, Summer, Graduate et VIE. Les fiches
affichent les preuves de classification, l'année connue et les contradictions.
La veille ajoutée concerne uniquement les off-cycle et stages longs **2027**.
Les autres métiers, zones, règles d'expérience et exclusions restent appliqués.

190 fiches de stages ont été recalculées sans collecte ni alerte historique.
19 stages actifs off-cycle/longs 2027 sont confirmés et atteignent le seuil de
priorité. D'autres stages ont un format ou une année à vérifier : leur affichage
ne les rend pas automatiquement admissibles aux alertes. Les Summer restent
hors des alertes de stages. Les scores des offres hors stages n'ont pas été
recalculés pendant cette publication.

Chaque source établit sa référence silencieuse au prochain passage complet
du radar sous les nouvelles règles, puis peut alerter les nouvelles offres.
Une collecte partielle ou en échec n'établit pas cette référence. À 20:13 UTC,
Jane Street avait terminé sa référence ; les autres étaient encore en attente
du passage programmé. Le radar était actif, en collecte, avec une pulsation
datant de deux secondes et les alertes et commandes Telegram activées.

La révision 110.1 ajoute un refus explicite des alertes pour les alternances et
Discovery/Insight reconnus, même si le contrat est omis. Elle conserve les
scores, les données et l'instant de référence de la première publication.

## Conservation et exploitation

- Sauvegarde SQLite cohérente créée et vérifiée avant publication.
- Schéma 4, même fichier et même inode ; aucune restauration de base.
- 958 offres et 958 suivis de candidature conservés.
- 39 alertes envoyées et 78 entrées d'historique conservées à l'identique.
- Curseur Telegram et liaison au destinataire conservés.
- Aucune alerte historique ajoutée par le recalcul.
- 24 sources actives conservées, sans activation du catalogue entier.
- Les cinq services tournent, avec zéro redémarrage inattendu et reprise Docker
  `unless-stopped` ; Docker et les unités cloud, Dashboard et Remote Commander
  restent actifs et activés au démarrage.
- Dashboard HTTP 200 via le lien HTTPS existant, sans connexion, avec données
  en direct et filtre Programme ; racine et mauvais lien 404, écritures 405,
  fichiers privés 404. Données et configuration montées en lecture seule,
  utilisateur 10001, aucun identifiant Telegram dans le Dashboard.
- Blocage temporaire de `sudo` rétabli à sa liste initiale après les contrôles.

Les incidents persistants sont BNP Paribas (HTTP 403, source ancienne) et
Nomura Campus (CAPTCHA, laissé en attente conformément au choix du propriétaire).
22 sources étaient à jour lors du contrôle. Aucun CAPTCHA n'a été contourné.

## Vérification

4 945 tests de régression passent. Après les derniers ajustements : 132 tests
de programmes, scoring et collecte, 144 tests de données/rendu/Dashboard direct,
151 tests de routes et suivi, ainsi que 13 tests JavaScript passent.
Ruff et mypy passent sur les 102 fichiers source. L'image a été construite sur
le VPS ; un audit en conteneur sans réseau, avec les données en lecture seule,
a précédé le recalcul et les vérifications en production.
La révision du garde-fou passe 113 tests ciblés et un contrôle synthétique dans
l'image finale, sans réseau.

Voir [le périmètre et la prochaine architecture](INTERNSHIPS-ARCHITECTURE.md).
