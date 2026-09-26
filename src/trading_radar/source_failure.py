"""Public, bounded explanations; never expose raw transport errors or URLs."""

import re


def failure_summary(message: object) -> dict[str, str]:
    text = message.lower() if isinstance(message, str) else ""
    if "captcha" in text:
        return {"code": "captcha", "label": "Le site demande un CAPTCHA."}
    if "robots policy disallows" in text:
        return {"code": "robots_denied", "label": "Le site interdit cet accès automatisé."}
    if "access restricted" in text:
        return {"code": "access_restricted", "label": "Le portail refuse temporairement l’accès."}
    if "http 429" in text or "server requests a later retry" in text:
        return {"code": "rate_limited", "label": "Le site demande d’espacer les tentatives."}
    if "macquarie public portal error page" in text:
        return {"code": "portal_error", "label": "Le portail renvoie vers sa page d’erreur."}
    if re.search(r"\bhttp 5\d\d\b", text):
        return {"code": "portal_error", "label": "Le serveur employeur est indisponible."}
    if re.search(r"\bhttp 30[12378]\b", text):
        return {"code": "redirect", "label": "Le portail renvoie une redirection inattendue."}
    if any(term in text for term in ["timeout", "time budget", "timed out", "transport error"]):
        return {"code": "timeout", "label": "La connexion ou la collecte n’a pas abouti à temps."}
    if any(term in text for term in ["pagination", "repeated", "total changed", "short page"]):
        return {
            "code": "pagination",
            "label": "Les pages de résultats sont incohérentes ; import interrompu.",
        }
    if any(
        term in text for term in ["missing", "invalid", "mismatch", "ambiguous", "expected json"]
    ):
        return {
            "code": "format_changed",
            "label": "La réponse ne correspond pas au format attendu.",
        }
    return {"code": "unavailable", "label": "La collecte n’a pas pu être validée."}
