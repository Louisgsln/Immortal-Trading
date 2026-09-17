# Audit de couverture — lot 21

17 septembre 2026, 02:20 à Paris (00:20 UTC). Audit borné de deux accès publics et de catalogues déjà conservés. Aucun import, recalcul en base, envoi ou activation de source par cet audit.

## Citadel Securities et JPMorgan : accès toujours indisponible

Le client HTTP du projet a tenté les seules pages déjà configurées, avec son User-Agent normal, ses règles robots, un espacement de deux secondes et zéro nouvelle tentative. Il commence obligatoirement par `robots.txt`.

| Source | Page demandée | Réponse effective | Requêtes |
| --- | --- | --- | ---: |
| Citadel Securities | [Open opportunities](https://www.citadelsecurities.com/careers/open-opportunities/) | `https://www.citadelsecurities.com/robots.txt` : HTTP 403 | 1 |
| JPMorgan | [Candidate Experience CX_1001](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/) | `https://jpmc.fa.oraclecloud.com/robots.txt` : HTTP 403 | 1 |

Les pages carrières elles-mêmes ne sont donc pas demandées. Ce résultat confirme une impossibilité de collecte depuis cet environnement, pas une absence d'offres ni une interdiction universelle d'accès au portail. Aucun endpoint alternatif, changement d'identité, authentification, proxy ou contournement n'a été essayé. Aucun outil d'indexation web n'a été utilisé pour prétendre valider l'accès du collecteur.

Les sources restent désactivées. Citadel a encore besoin d'une découverte d'interface publique autorisée puis d'un connecteur et de tests réels. JPMorgan a déjà un adaptateur testé hors réseau ; son activation exige un accès public fonctionnel et une validation de pagination, détails, identité et robots. Installer un connecteur tiers ne démontrerait pas à lui seul cet accès.

Preuve locale : `data/discovery/lot21/coverage/access-probe.json` contient les deux URLs réellement lues, statuts et horodatages. Aucun cookie ni en-tête de session n'y est conservé.

## Corpus technique local et état avant correction

Deux réponses publiques complètes du lot 12 sont disponibles :

| Source | Artifact local | Annonces brutes | Retenues par le code avant correction |
| --- | --- | ---: | ---: |
| Jump Trading | `data/discovery/lot12/2d6ba1702416.html` — contenu JSON Greenhouse | 108 | 23 |
| XTX Markets | `data/discovery/lot12/058eb18a512b.html` — contenu JSON Greenhouse | 10 | 1 |

La provenance et la concordance des catalogues publics ont été vérifiées au [lot 12](VALIDATION-LOT12.md). Le présent audit relit leurs descriptions intégrales, départements et types de contrat, puis exécute le parseur et le score actuels uniquement en mémoire. Les empreintes SHA-256 et douze exemples sélectionnés figurent dans `local-analysis-before-change.json`. Il ne revérifie pas l'ouverture actuelle de ces postes et ne mesure pas toute la couverture technique des vingt employeurs.

### Exemples de pertes et de classement prudent

| Offre officielle / référence | Observation dans le corpus avant correction | Preuve et réserve |
| --- | --- | --- |
| [Python Software Engineer — 8104832](https://www.jumptrading.com/hr/job?gh_jid=8104832) | Écartée avant scoring : titre sans terme du filtre | Core Development ; missions de conception avec les traders dans `What You'll Do` ; minimum de deux ans de Python. Contrat Experienced, aucune date de début. Bon candidat pour une extension bornée. |
| [Quantitative Developer — 7822791](https://www.jumptrading.com/hr/job?gh_jid=7822791) | Écartée avant scoring | Front Office ; introduction propre au rôle décrivant développement d'infrastructure avec les chercheurs quantitatifs, puis cycle de développement et dépannage de production dans les missions. Rôle mixte, qualification prudente nécessaire. |
| [Quantitative Developer / Trading Team — 6190021](https://www.jumptrading.com/hr/job?gh_jid=6190021) | Déjà collectée, score total 0 | Description très proche de 7822791, mais les expressions exactes attendues par le score technique manquent. La collecte seule ne suffit donc pas à corriger le classement. |
| [Quantitative Developer / Trading Team — 7767735](https://www.jumptrading.com/hr/job?gh_jid=7767735) | Déjà collectée, score total 0 | Production, interventions en séance, outillage, recherche de microstructure. Expérience et autonomie demandées : ne pas convertir le rattachement Front Office en statut junior. |
| [Quantitative Developer / Trading team — 6172858](https://www.jumptrading.com/hr/job?gh_jid=6172858) | Déjà collectée, score total 0 | Missions mixtes recherche/infrastructure. La description demande un historique de cinq ans ou plus ; le libellé `5+ year track record` n'est pas reconnu comme expérience minimale par les règles actuelles. Préserver cette réserve avant d'élargir le score. |
| [Quantitative Developer / Trading Team — 8105914](https://www.jumptrading.com/hr/job?gh_jid=8105914) | Déjà collectée, score total 0 | Production engineering/trade support et minimum textuel ambigu `2-5+ years`. Le score courant détecte aussi une exclusion d'expérience ; pas de requalification automatique en junior. |

Le score nul ci-dessus résulte de l'exclusion technique, même lorsque ses composantes individuelles affichent des points. Une annonce écartée avant normalisation n'a pas de score calculé : cela n'équivaut pas à un score nul.

### Contre-exemples à conserver

- [Jump Software Engineer — 7156979](https://www.jumptrading.com/hr/job?gh_jid=7156979) : département Core Development, mais missions d'outillage transversal et de productivité des développeurs, avec au moins cinq ans d'expérience. Le département ou la présentation générale de Jump ne suffisent pas.
- [Jump Market Data Systems — 7847009](https://www.jumptrading.com/hr/job?gh_jid=7847009) : missions techniques liées au trading démontrées, mais rôle présenté comme senior dans le texte et cinq ans ou plus d'expérience. Un titre sans Senior ne prouve pas l'éligibilité junior.
- [Jump Campus C++ Software Engineer — 8027860](https://www.jumptrading.com/hr/job?gh_jid=8027860) : technologie de trading, mais contrat de stage. L'élargissement du filtre ne doit pas lever l'exclusion des stages prioritaires.
- [XTX C++ Software Engineer — 7831489003](https://job-boards.greenhouse.io/xtxmarketstechnologies/jobs/7831489003) : déjà reconnu par département et rubrique de missions, score 65. Sert de contrôle positif.
- [XTX Machine Learning Performance Engineer — 7741365003](https://job-boards.greenhouse.io/xtxmarketstechnologies/jobs/7741365003) : même département Tradingdev ETD Tech, mais fonction accélération ML/compilation ; reste un contrôle négatif de la règle dédiée au développement du trading.
- [XTX Software Developer / Shared Engineering — 7835362003](https://job-boards.greenhouse.io/xtxmarketstechnologies/jobs/7835362003) : outils internes, CI/CD, inventaire et expérience développeur ; présentation de société algorithmique insuffisante pour prouver une mission de trading intégrée.

## Recommandation d'implémentation

Commencer par Jump, avec preuves explicites dans les missions propres au poste et tests négatifs de département seul, présentation générique, compétences seules, stage et expérience senior. Conserver séparément rôle technique, contrat et expérience. Ne pas ajouter globalement `software`, `developer` ou `engineer` au filtre de tous les employeurs.

Un élargissement à Quantitative Developer doit distinguer développement directement intégré et support de production, et traiter les exigences d'expérience avant de rendre ces rôles prioritaires. Le titre et le rattachement organisationnel ne suffisent pas. La règle XTX existante n'a pas besoin d'être généralisée à ses autres départements.

## Reproduction et limites

```powershell
.venv/Scripts/python.exe scripts/audit_lot21.py
# Option explicite : deux contrôles d'accès publics, arrêt au premier refus de chaque source.
.venv/Scripts/python.exe scripts/audit_lot21.py --network
```

Le script dépend des deux artifacts locaux du lot 12, ignorés par Git. Sans ces preuves, il échoue plutôt que d'annoncer une analyse vide. Il ne touche pas SQLite et ne crée ni notifier ni collecteur de scan. Une relance reflète le code du moment et remplace `local-analysis.json` ; le fichier `local-analysis-before-change.json` préserve l'état antérieur à la correction du lot 21. Les résultats de cette correction doivent être lus dans le bilan de validation du lot, distinctement du présent diagnostic.
