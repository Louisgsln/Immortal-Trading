# Accès Nomura depuis une session validée

Le portail campus officiel peut demander un CAPTCHA. La validation effectuée
dans le navigateur intégré ne transmet pas sa session au scanner. Le mode
optionnel décrit ici conserve uniquement la session d'une fenêtre dédiée au
portail public Nomura, puis l'utilise pour lire les mêmes pages depuis le radar.

**La compatibilité avec le portail doit être confirmée par une collecte réelle
avant activation.** Une validation du navigateur ne prouve pas, à elle seule,
que le serveur accepte ensuite la session depuis le collecteur HTTP.

## Préparer la session

Installer l'option `browser` depuis le fichier de dépendances verrouillé, puis
exécuter depuis le dossier du projet :

```powershell
uv sync --locked --extra browser
uv run --no-sync python scripts/prepare_nomura_session.py --destination data/nomura-session/session.json --channel msedge
```

Une fenêtre Edge séparée s'ouvre, sans utiliser le profil personnel du navigateur.
Valider le CAPTCHA et le bouton Continue si le site les présente. Ne pas se
connecter à un compte candidat. Le programme attend au maximum cinq minutes.
Il vérifie le tableau complet et la présence du lien de connexion public avant
de conserver les cookies du domaine Nomura et de fermer la fenêtre.

Le programme ne coche ni ne résout aucun CAPTCHA, ne soumet aucune candidature
et ne s'inscrit à aucune alerte employeur. Une fermeture de la fenêtre, une
sortie du domaine ou une vérification incomplète ne remplace pas la session locale.

## Relier le radar

Après une collecte de validation sur copie, renseigner dans le `.env` local :

```dotenv
NOMURA_SESSION_FILE=data/nomura-session/session.json
```

Redémarrer le scanner une fois pour prendre en compte ce réglage. Les prochains
renouvellements du même fichier sont lus à chaque collecte, sans redémarrage.
Une validation postérieure au dernier échec permet une tentative de reprise
sans attendre la fin du délai d'échec ; si cette tentative échoue, le délai
habituel s'applique de nouveau. Les contrôles de robots, de cadence, de format,
d'identité et les budgets de temps restent actifs.

Sans ce réglage, le fonctionnement HTTP anonyme habituel reste utilisé.
Le fichier n'est pas joint aux offres, exports, sauvegardes métier ou commits.
Conserver ce fichier sous `data/`, exclu de Git ; ne jamais le partager.
Le cookie est envoyé exclusivement à `https://nomuracampus.tal.net` et dans
son périmètre de chemin. Les journaux ne doivent jamais afficher son contenu.

## Renouveler

Le serveur peut révoquer ou expirer son cookie. Le radar limite aussi sa
réutilisation à douze heures après validation et refuse une session absente,
invalide ou expirée. L'état de la source demande alors de renouveler l'accès
dans le navigateur. Relancer la commande de préparation et valider le contrôle
présenté. La lecture automatique ne peut pas être garantie sans interruption :
un nouveau CAPTCHA demande une intervention, les anciennes offres sont conservées.

Références : [portail indiqué par Nomura](https://www.nomura.com/careers/early-careers/apply-to-nomura/)
et [gestion des sessions Playwright](https://playwright.dev/python/docs/auth).
