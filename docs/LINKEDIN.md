# Annonces LinkedIn — lot 179

Installation sur le VPS en attente d’autorisation ; voir le [bilan](VALIDATION-LOTS177-179.md).

La commande privée `/linkedin` ajoute une annonce copiée dans Telegram au Dashboard.
Elle répond avec la fiche et les boutons « Ajouter à la liste des souhaits » et
« J’ai postulé ». Le suivi, le tri et le retrait des souhaits utilisent les mêmes
fonctions que pour les offres déjà collectées.

Envoyer ce modèle en un seul message, puis remplacer les exemples par l’annonce réelle :

```text
/linkedin
Entreprise: Bank of America
Poste: Global Markets Sales and Trading 2027 Off-Cycle Analyst
Lieu: Milan, Italie
Lien: https://www.linkedin.com/jobs/view/1234567890/
Description: coller ici le texte complet de l’annonce
```

La description peut occuper plusieurs lignes et doit venir en dernier. Entreprise,
poste, lieu et lien sont obligatoires. Le numéro de référence est extrait du lien
public LinkedIn ; les paramètres de suivi sont retirés. Une information absente
n’est pas inventée. Les règles habituelles analysent le texte pour le score, les
stages off-cycle/longs et les dates explicites.

L’import reste marqué **manuel, ouverture à confirmer**, dans Telegram et sur les
vues PC et téléphone du Dashboard. Il ne constitue pas une vérification récente
par le site employeur, ne compte pas comme une source ou un employeur surveillé,
et ne crée aucune alerte dans le journal des envois automatiques. La confirmation
directe à l’utilisateur contient sa fiche. Le curseur existant empêche le rejeu
automatique d’une commande.

Un nouvel import de la même référence conserve la fiche et le suivi existants.
Une correspondance unique avec une offre officielle ne remplace pas sa description,
ne rafraîchit pas son observation et ne rouvre pas une offre fermée. Les rapprochements
ambigus restent distincts. Une annonce manuelle ne compte pas comme une preuve de
source active : elle ne bloque pas une fermeture ultérieure confirmée par l’employeur.
Le score ne reçoit aucun bonus lié à LinkedIn.

Le 19 octobre 2026, les règles publiques LinkedIn chargées par le client du radar
interdisent les routes de recherche, de fiches et de l’API anonyme jobs-guest depuis
le VPS. Ce lot ne contourne pas ces règles, ne demande aucun cookie ou mot de passe
LinkedIn, et n’active pas JobSpy pour ce site. Il n’assure pas une détection automatique
de toutes les annonces LinkedIn. L’import d’alertes reçues par e-mail reste une
option distincte nécessitant l’accord sur la lecture des seuls e-mails concernés.

[Carnet des tâches](TASK-BOARD.md) · [Validation et installation](VALIDATION-LOTS177-179.md).
