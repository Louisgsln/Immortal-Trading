# Modifier le suivi depuis le dashboard

Le serveur local peut modifier les candidatures déjà présentes dans votre base.
Les statuts, contacts, notes et prochaines actions restent sur ce poste.
Enregistrer « Postulé » consigne votre décision ; cela n'envoie rien à
l'employeur. La date de candidature reste une saisie explicite.

## Démarrer

Depuis la racine du projet :

```powershell
trading-radar dashboard serve --edit-applications --port 8765
```

Ouvrir `http://127.0.0.1:8765/`, choisir une offre puis **Modifier le suivi** dans
sa fiche. Le bouton relit le suivi actuel avant d'ouvrir le formulaire. Choisir les
champs, puis **Enregistrer le suivi**. Les règles de dates, de statuts et de longueur
sont celles du [suivi en ligne de commande](APPLICATIONS.md).

Un champ facultatif vide efface sa valeur. Une prochaine action datée exige un
libellé ; pour retirer l'action entière, vider aussi sa date. Seuls les champs
modifiés sont envoyés. Une saisie identique ne crée pas d'entrée d'historique.

Le badge de la fiche, les lignes, le filtre de statut et le compteur des candidatures
en cours se mettent à jour après sauvegarde. Le suivi est aussi relu toutes les dix
secondes lorsque la page est visible, notamment après **J’ai postulé** dans Telegram.
Une modification externe conserve le brouillon ouvert et impose une relecture
avant sauvegarde. Une interruption de synchronisation est signalée en bas de page.
Recharger la page après un redémarrage du serveur renouvelle la session locale.
Recharger la page relit toutes les
offres, la santé et les tendances. Ce mode ne lance aucune collecte automatique.
Le CSV et les exports HTML déjà créés nécessitent toujours un nouvel export.

## Brouillons et conflits

Une fermeture du détail ou une annulation demande d'abandonner explicitement un
brouillon modifié. Pendant une requête, les commandes sont désactivées pour éviter
un double enregistrement. Un brouillon n'est pas conservé après fermeture du navigateur.

Si le suivi a changé depuis son ouverture, la sauvegarde est refusée. Le brouillon
reste visible et **Recharger le suivi** permet de reprendre la version récente,
après confirmation de l'abandon. Aucun champ concurrent n'est écrasé silencieusement.
Cela couvre aussi les modifications réalisées avec la commande `applications update`.

Si la réponse réseau est perdue, l'interface ne peut pas savoir si la sauvegarde
a abouti. Elle demande une relecture, sans renvoyer automatiquement la modification.
Une erreur de validation connue laisse corriger le formulaire.

## Historique

Après lecture ou sauvegarde, ouvrir **Historique du suivi** pour voir les champs
avant/après. Les 50 dernières modifications sont affichées ; le total et une
indication de troncature signalent un historique plus long. La commande
`applications history JOB_ID` permet de consulter l'historique complet.

Effacer une note dans le formulaire ne la retire pas des anciennes entrées de
l'historique. La fiche et son historique sont enregistrés ensemble dans une même
transaction, sous le verrou également utilisé par les scans.

## Modes et limites

- `dashboard serve` sans option reste un instantané en lecture seule.
- `dashboard export` reste un fichier autonome en lecture seule, sans accès à l'API.
- `--edit-applications` active uniquement le suivi local : aucune écriture des offres,
  des scores, de la configuration, des alertes ou des archives de santé.
- Le serveur écoute sur `127.0.0.1`, vérifie l'origine des écritures et exige un jeton
  de session inclus dans la page. Redémarrer le serveur renouvelle ce jeton.
- La base doit exister et avoir le schéma courant. Le serveur ne la crée ni ne la migre.
- Les formulaires JSON sont limités à 128 Kio. Les erreurs ne renvoient pas les notes
  privées, les chemins locaux ou les détails SQL.

Ce serveur est destiné à un usage personnel local. Il ne fournit pas de comptes
multiutilisateurs ni de déploiement public. L'arrêter avec `Ctrl+C` ferme l'éditeur.
