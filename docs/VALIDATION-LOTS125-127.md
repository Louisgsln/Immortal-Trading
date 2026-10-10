# Lots 125–127 — audit, employeurs et qualité du radar

## Observation avant livraison

Le 10 octobre 2026, 25 sources étaient activées sur le VPS, contre 86 dans la
configuration de développement. Sur les sept jours observés : 80 premières
découvertes, 30 avec score ≥70 et 19 alertes envoyées. Ces découvertes incluent
19 fiches du premier import Morgan Stanley campus, dont 11 au score ≥70.
Les tableaux comptent les découvertes du radar, pas des dates de publication.
La base contenait 1 013 offres ; le volume global est distinct du flux nouveau.

Les catalogues Greenhouse de 43 sources ont été relus. L’extension de 38 sources
absentes du VPS représente 1 486 postes de catalogue examinés, 306 fiches
sélectionnées et 76 au score ≥70 avant qualification supplémentaire Old Mission.
Les catalogues sans offre ciblée sont distingués des erreurs de collecte.

## Lot 125 — bilan hebdomadaire consultable

Le Dashboard affiche découvertes, scores au seuil et offres actuellement à
examiner. Les motifs de non-disponibilité sont comptés : hors cible, score bas,
échéance, source ancienne, conditions de stage et suivi. `trading-radar weekly`
expose le même bilan en lecture seule, sans notes de candidature ni envoi Telegram.
L’éligibilité de consultation est partagée avec Telegram dans un module indépendant.
Les premiers imports sont explicitement inclus ; le bilan n’affirme pas compter
les alertes envoyées ni les publications employeur.

## Lot 126 — profil OVH étendu

Le profil [vps-companies.yaml](../config/vps-companies.yaml) conserve les 30
définitions existantes et ajoute 38 sources, dont deux portails Chicago Trading
et deux portails Radix. Cible : 63 sources activées, 56 employeurs. Les settings
de production, le seuil 70, les métiers et les régions restent conservés.
Chaque catalogue a réussi deux lectures publiques. L’import initial est silencieux
et établit les références stages avant les prochaines détections.

## Lot 127 — corrections fondées sur des annonces

Old Mission publie désormais `Intern` dans Employment Type ; Point72 publie aussi
`Part Time` dans Time Type. Ces valeurs sont conservées ; les valeurs inconnues
restent refusées. Un contrat ne suffit pas à confirmer un stage long ou off-cycle.

Les annonces Old Mission Fundamental Research Analyst et Quantitative Researcher
graduate 2027 décrivent des missions d’analyse influençant les décisions de trading
et de modélisation des options. La sélection et le score retiennent ces missions
dans une rubrique Responsibilities unique. Contre-exemples : mauvais employeur,
agrégateur, titre sans missions, texte d’entreprise, rubrique dupliquée ou déplacée.

Un aperçu des scores historiques a détecté 33 différences de champs dérivés,
dont 11 scores liés à l’ancienne application du filtre Associate. La réconciliation
ne crée pas d’alertes et préserve les identifiants et le suivi des candidatures.

## Limites d’accès observées

BNP Paribas renvoie HTTP 403 depuis le VPS ; l’ancienne base n’est pas fermée
par déduction. Optiver garde une lacune explicite sur Trading Automation Specialist.
Nomura professionnels a réussi sa lecture ; Nomura campus reste laissé en attente
si CAPTCHA. Des 503 Workday et une redirection Barclays sont consignés au carnet.

## Validation et installation

Tests et image en cours de validation ; la livraison ne sera déclarée installée
qu’après sauvegarde vérifiée, essai sur copie, contrôle des imports silencieux,
redémarrage et observation HTTPS, services et conservation des historiques.
