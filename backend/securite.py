import unicodedata

EXT_RISQUE = (".exe", ".js", ".scr", ".bat", ".cmd", ".vbs", ".jar", ".msi", ".docm", ".xlsm")
SECRETS = ("mot de passe", "password", "code bancaire", "carte bancaire", "numero de carte", "code secret", "identifiants", "code pin", "iban")
URGENCE = ("urgent", "immediat", "sous 24", "suspendu", "sera ferme", "sera bloque", "derniere chance", "expire")
DESINSCRIPTION = ("se desinscrire", "desinscription", "unsubscribe")
EXPEDITEURS_PUB = ("noreply", "no-reply", "newsletter", "news@", "promo", "marketing")
MOTS_PROMO = ("offre", "promo", "soldes", "reduction", "-50")


def _texte(email):
    brut = " ".join([email.objet or "", email.extrait or "", email.texte_pj or ""]).lower()
    return "".join(c for c in unicodedata.normalize("NFD", brut) if unicodedata.category(c) != "Mn")


def detecter_danger(email, noms_pj=()):
    """Retourne (type, detail) si l'email est dangereux, sinon None."""
    for nom in noms_pj:
        if (nom or "").lower().endswith(EXT_RISQUE):
            return "piece_jointe", "piece jointe a risque : " + nom
    t = _texte(email)
    secret = [m for m in SECRETS if m in t]
    urgence = [m for m in URGENCE if m in t]
    if secret and urgence:
        return "hameconnage", "demande de donnees sensibles (" + secret[0] + ") avec urgence (" + urgence[0] + ")"
    return None


def detecter_publicite(email):
    t = _texte(email)
    if any(m in t for m in DESINSCRIPTION):
        return True
    exp = (email.expediteur or "").lower()
    return any(m in exp for m in EXPEDITEURS_PUB) and any(m in t for m in MOTS_PROMO)
