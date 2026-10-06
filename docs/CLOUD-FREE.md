# Scanner sur un hôte gratuit

Ce guide conserve le choix étudié pour le budget initial de 0 €. Le propriétaire
a ensuite choisi **OVH** et confirmé ne pas avoir encore de compte ni de VPS.
La procédure actuelle commence dans [OVH-SETUP.md](OVH-SETUP.md).
La migration et l'exploitation communes se trouvent dans
[CLOUD-DEPLOYMENT.md](CLOUD-DEPLOYMENT.md).

Préparation initiale du **6 octobre 2026**, lot 103. Budget alors confirmé : **0 €**.
La configuration est prête pour une VM Linux accessible ; aucune VM, aucun
compte d'hébergement et aucune collecte de production ne sont créés par ce lot.

## Hôte proposé

Oracle Cloud propose des ressources **Always Free** distinctes de son essai
temporaire. Sa documentation actuelle donne, pour Ampere A1, une enveloppe
gratuite partagée de **2 OCPU et 12 Go**, avec 200 Go de volumes dans la région
d'origine. Une VM Ubuntu 24.04 de **1 OCPU, 2 Go et 50 Go de disque** suffit comme
point de départ pour ce radar ; vérifier les ressources déjà consommées et les
labels/prix de la console avant toute création. L'inscription demande généralement
un téléphone et une carte ; ne pas convertir le compte en abonnement payant.
Sources officielles consultées le 6 octobre :
[ressources Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm),
[compte Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm).

La capacité gratuite peut être indisponible et une VM peu utilisée peut être
reprise par Oracle. Le déploiement fonctionne sur une VM gratuite adaptée, mais
n'apporte pas une garantie de disponibilité 24 h/24. Aucun trafic artificiel
ni charge factice n'est ajouté pour modifier les critères d'inactivité.
Si la console propose seulement des ressources payantes, conserver le budget
zéro et interrompre la création. Le fichier `deploy/cloud-init.yaml` installe
les outils sur une VM Ubuntu choisie ; il ne provisionne rien chez l'hébergeur.

## Installer et migrer

Une fois la VM choisie et accessible, suivre le
[guide commun de déploiement](CLOUD-DEPLOYMENT.md). Il décrit l'accès, la
restauration de la base Windows, la bascule des processus et les sauvegardes.
