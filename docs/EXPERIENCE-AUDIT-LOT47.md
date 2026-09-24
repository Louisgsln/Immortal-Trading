# Lot 47 — Exigences d'expérience encore non reconnues

Audit hors ligne du **24 septembre 2026**, sur une sauvegarde restaurée et
vérifiée des **872 offres**. Les dates employeur et de collecte ne sont pas
rafraîchies par cet audit.

## Périmètre de la correction

1. Fourchettes contenant le qualificatif `prior`, comme `1-4 years of prior
   work experience`. La borne basse reste retenue ; les protections existantes
   sur les préférences, négations et alternatives continuent de s'appliquer.
2. Exigence explicite de diplôme **et** d'expérience, avec chiffre écrit deux
   fois : `Requires a Master's degree … and three (3) years of experience`.
   Le mot et le nombre doivent correspondre (zéro à dix). Le verbe d'obligation,
   le diplôme, la conjonction et la mention d'expérience sont obligatoires.

Une conversion générale des nombres écrits en chiffres n'est pas ajoutée.
Les voies alternatives, mentions facultatives, bornes maximales, nombres
contradictoires et durées de formation/contrat sont écartés dans les cas testés.
Les anciennes règles `degree … plus N years` restent couvertes par régression.

## Effet mesuré sur tout le corpus

| Offre | Preuve dans la description conservée | Minimum avant → après | Score avant → après |
| --- | --- | --- | --- |
| Deutsche Bank — Trader, R0452740 | `and three (3) years of experience` après le diplôme requis | inconnu → 3 ans | 75 → 70 |
| Deutsche Bank — IB - FX Options Trader - Associate, R0450097 | `1-4 years of prior work experience` dans les compétences requises | inconnu → 1 an | 78 → 78 |
| Goldman Sachs — SMM IRP Trading Strat, Associate, London | `0-3 years of prior work experience` dans Basic Qualifications | inconnu → 0 an | 66 → 66 |
| Goldman Sachs — G10 STIR/Repo Trader, Analyst/Associate, Tokyo | `2-5 years of prior work experience` dans Basic Qualifications | inconnu → 2 ans | 88 → 88 |

Les **868 autres indicateurs** ne changent pas. Les anciens scores stockés
concordaient tous avec l'ancien programme : aucun recalcul latent sans rapport
avec ce lot n'a été découvert. Seule la décomposition du premier score change,
avec la composante junior 5 → 0 et l'explication du minimum supérieur à deux ans.

**Trois ans ne supprime pas automatiquement une offre.** Le score corrigé reste
70, donc au seuil des alertes actuel. La règle existante d'exclusion numérique
commence à cinq ans ; ce lot ne modifie pas cette politique. Zéro reconnu ne
signifie pas non plus absence de tout autre prérequis.

## Répétition avant application

La correction a été exécutée sur la copie restaurée : un score corrigé,
871 lignes d'offres strictement inchangées, huit tables métier inchangées
(candidatures, alertes, états des sources et historique des scans compris).
Un événement `rescored` et une entrée d'historique du score sont ajoutés.
Le second passage ne modifie aucune des onze tables ; intégrité et relations
SQLite vérifiées. Aucune notification ni requête employeur n'est envoyée.

Preuves locales hors Git : `data/windows-service/lot47-audit-backup.json`,
`lot47-audit-restore.json`, `lot47-before.json`, `lot47-after.json`,
`lot47-impact.json` et `lot47-rehearsal-proof.json`.
