# Lot 82 — Comparaison des pages UBS et vérification Nomura

## UBS

Incident observé le 26 septembre à 23:13 : la relecture de la première page
interrompt l'import avec « UBS board changed during pagination ». Deux lectures
publiques du portail campus ont ensuite renvoyé les mêmes 50 identifiants et
exactement les mêmes contenus, dans un ordre différent. Le catalogue comporte
154 offres campus et 532 offres professionnelles lors du diagnostic.

La comparaison ne dépend plus de la position des lignes dans cette page.
Chaque ligne reste intégralement comparée par identifiant : un changement de
titre, description, date, lien ou autre champ reste détecté. Les doublons sont
rejetés avant de construire cette correspondance, y compris lors de la relecture.
La structure des champs et les liens publics sont également validés à ce stade.

Les contrôles du total, des pages courtes et des doublons entre pages restent
actifs. Une modification réelle permet une seule reprise intégrale ; une seconde
incohérence interrompt l'import. Les déplacements d'offres entre pages ne sont
pas assimilés à une simple permutation. Le budget et la cadence restent
inchangés ; aucun import partiel supplémentaire, aucune clôture par absence.

Neuf cas de test supplémentaires couvrent la permutation sans reprise,
cinq modifications de contenu et trois relectures malformées sans reprise.
Les tests existants couvrent le remplacement d'un identifiant, les changements
de total, les doublons entre pages, les limites et le CAPTCHA.

## Nomura campus

Le portail public affiche un CAPTCHA « I'm not a robot » suivi de « Continue ».
Après confirmation du propriétaire, cette vérification a été effectuée dans
le navigateur. La liste de **44 offres** est alors accessible. Aucun formulaire
de candidature ni inscription à des alertes employeur n'a été soumis.

Une nouvelle tentative HTTP après cette validation reçoit encore le CAPTCHA :
l'accès du navigateur ne se transmet pas au scanner. La source automatique reste
donc signalée comme bloquée. Aucun cookie de navigateur n'est exporté ou stocké
dans le dépôt et aucun mécanisme de résolution automatique n'est ajouté.

## Validation et livraison

Collecte réelle sur copie : les deux sources UBS réussissent, **48 offres lues,
69 requêtes**, aucune offre nouvelle ou modifiée, aucune clôture ni alerte.
Les scores, suivis et historiques existants sont identiques avant et après.

Validation locale : **3 997 tests réussis, 4 ignorés**. Format et lint de
244 fichiers, analyse statique de 88 modules réussis. Les résultats de
l'installation et des contrôles GitHub sont consignés après leur vérification.
