# Régressions indépendantes des qualifications — lot 29

## Périmètre

Le fichier `tests/test_qualification_regressions.py` couvre les neuf cas vérifiés dans
[l’audit du lot 28](QUALIFICATION-AUDIT-LOT28.md), treize contre-exemples de portée et
sept contrôles du score. Les extraits sont courts et les employeurs anonymisés dans
les tests. Aucune lecture de la base locale ni aucun réseau n’est nécessaire pour
exécuter ces 29 cas.

Les attentes visent deux corrections locales :

- `Experience Desirable: 1+ years ...` devient une préférence textuelle, sans
  modifier le minimum structuré fourni par l’employeur.
- Le diplôme ou son équivalent **plus sept ans d’expérience** conserve les sept
  ans comme exigence additive ; la substitution d’expérience à l’éducation ne
  supprime pas cette exigence.

Les deux préférences Goldman déjà corrigées restent facultatives. Les cinq minima
indépendants de l’audit sont conservés : 2, 8, 10, 5 et 3 ans. Une préférence pour
une formation, une discipline ou une équipe ne supprime pas un minimum distinct.

## Effets vérifiés sur le score

Une version réduite des signaux de l’offre SIG reproduit le score de 65 : rôle
technique lié au trading, marché actions/dérivés, profil C#/quantitatif/dérivés,
date de début inconnue, absence de preuve junior. L’ajout du passage de qualification
doit ramener le score à 0, la composante junior à 0 et produire l’exclusion
`requires at least 5 years of experience`.

La version réduite du cas CA conserve 82, avec son titre d’analyste, son activité
trading/crédit et son minimum structuré de 0. Le retrait du minimum textuel `[1]`
n’ajoute aucune nouvelle classification. Une autre offre sans signal junior reste
classée `unknown`, avec une composante junior de 5. Ces résultats de classement ne
constituent pas une détermination d’éligibilité du candidat.

Les minima structurés de 3 et 5 ans restent applicables malgré la préférence
textuelle. Les exclusions d’autres rôles restent actives. Les mentions d’expérience
de l’entreprise et les phrases sans exigence numérique ne deviennent pas des
contraintes de candidature.

La revue indépendante a aussi détecté une alternative au parcours non reconnue :
`Bachelor's degree plus 7 years of experience, or MSc with no prior experience`.
Les variantes `an MBA` et `M.Sc.` sont couvertes pour empêcher de transformer une
contrainte propre à un parcours en minimum universel. Le résultat attendu est `[]`
pour ces formulations ambiguës, sans inférer le minimum de l’autre parcours.

## Validation

- Exécution finale après intégration du parseur et correction des alternatives :
  **29 réussites**.
- Ruff : analyse et formatage conformes pour ce fichier.
- La comparaison exhaustive des 813 offres est une vérification distincte menée
  par l’agent principal ; elle n’est pas remplacée par les extraits de ces tests.

Commande :

```powershell
.venv/Scripts/python.exe -m pytest tests/test_qualification_regressions.py -q
```

## Limites

Les tests n’instaurent pas d’interprétation générale de toutes les alternatives
diplôme/expérience et ne propagent pas une préférence jusqu’à la rubrique suivante
dans un texte aplati. Les scénarios courts sont des régressions ciblées ; seuls les
résultats du rejeu complet établissent les effets sur le corpus conservé.
