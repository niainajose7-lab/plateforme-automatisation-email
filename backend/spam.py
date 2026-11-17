"""Detection simple de spam : des signaux ponderes, un seuil, des raisons lisibles."""
import re
import unicodedata

SEUIL = 2  # total des signaux a partir duquel l'email est classe 'spam'

FORTS = [  # poids 2 : phrases typiques d'arnaques
    "vous avez gagne", "felicitations vous", "loterie", "heritage", "bitcoin",
    "viagra", "compte suspendu", "compte bloque", "verifiez votre compte",
    "confirmez votre mot de passe", "cliquez ici pour", "gagnez de l'argent",
    "you have won", "click here to", "verify your account", "account suspended",
    "claim your prize",
]
FAIBLES = [  # poids 1 : mots souvent utilises par les spams
    "offre limitee", "gratuit", "urgent", "derniere chance", "promotion",
    "cliquez ici", "100% gratuit", "sans engagement", "act now", "free",
]
LIENS_COURTS = ("bit.ly", "tinyurl", "cutt.ly", "t.co/", "goo.gl", "rb.gy")


def _normaliser(texte):
    texte = unicodedata.normalize("NFD", (texte or "").lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def detecter_spam(email):
    """Retourne (est_spam, raisons) pour un objet Email."""
    objet = email.objet or ""
    corps = _normaliser(objet + " " + (email.extrait or ""))
    score, raisons = 0, []

    for phrase in FORTS:
        if phrase in corps:
            score += 2
            raisons.append(phrase)
    for mot in FAIBLES:
        if mot in corps:
            score += 1
            raisons.append(mot)
    if any(lien in corps for lien in LIENS_COURTS):
        score += 1
        raisons.append("lien raccourci")
    lettres = [c for c in objet if c.isalpha()]
    if len(lettres) >= 8 and sum(c.isupper() for c in lettres) / len(lettres) > 0.8:
        score += 1
        raisons.append("objet en majuscules")
    if objet.count("!") >= 2:
        score += 1
        raisons.append("points d'exclamation")

    return score >= SEUIL, raisons
