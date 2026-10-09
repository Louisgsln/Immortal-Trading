# Lot 111 — Portails campus et off-cycle

Validation du 7 octobre 2026 sur le VPS, avec Remote Desktop Commander.

- Morgan Stanley Global Programs : catalogue public paginé de 100 programmes, 22 requêtes avec le collecteur du radar et respect de robots.txt. Après le filtre métier affiné : 18 stages conservés, dont 11 stages 2027 prioritaires et admissibles à la politique off-cycle/stages longs.
- Les événements, formulaires de candidature et liens de session Oleeo sont exclus. Les liens conservés pointent vers les fiches publiques canoniques. Business Control est hors cible ; les stages de finance quantitative exigent des missions de pricing/hedging/trading vérifiées dans leur rubrique.
- JPMorgan Campus : adaptateur Oracle et recherches off-cycle/internship préparés. Le catalogue est accessible, mais robots.txt renvoie 403 au collecteur ; activation suspendue. Aucune exception robots ni contournement ajouté.
- Les recherches Workday et les portails bancaires validés établissent une référence de stages lorsque leur périmètre est entièrement collecté. Cette preuve est distincte du catalogue complet d'une entreprise : elle n'autorise aucune fermeture par absence.
- Premier import campus silencieux ; aucun historique d'alerte ou curseur Telegram réinitialisé. La configuration personnalisée de production est conservée, avec seulement les deux nouvelles entrées campus.

Tests : pagination incomplète/instable, doublons, événements, domaines étrangers, identité/titre/ville incohérents, liens de session, preuves métier, référence silencieuse puis alerte unique. Sauvegarde SQLite vérifiée avant déploiement et comparaison des identifiants/historiques après déploiement.

Les restrictions BNP et l'accès humain Nomura restent traités selon les contraintes précédentes. Une réponse publique de Nomura peut être collectée normalement ; aucune session CAPTCHA n'est préparée.
