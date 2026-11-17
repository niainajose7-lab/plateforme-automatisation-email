import re

from intelligence import normaliser

DEVISES = r"(?:€|eur(?:os?)?|usd|\$|mga|ariary|ar)(?![a-z0-9])"
MONTANT = re.compile(
    r"(\d{1,3}(?:[ .]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*" + DEVISES,
    re.IGNORECASE,
)
DATE = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b")
NUMERO = re.compile(
    r"facture\s*(?:n[°o]?\.?|no|numero)?[\s:]*([0-9a-z][0-9a-z\-/]*\d)",
    re.IGNORECASE,
)

MOTS_TOTAL = ("total", "net a payer", "montant", "a payer")
MOTS_ECHEANCE = ("echeance", "avant le", "date limite", "due")


def _nombre(texte):
    texte = texte.replace(" ", "")
    if "," in texte and "." in texte:
        texte = texte.replace(".", "").replace(",", ".")
    elif "," in texte:
        texte = texte.replace(",", ".")
    elif texte.count(".") > 1:
        texte = texte.replace(".", "")
    return float(texte)


def trouver_montant(texte):
    meilleur = None
    for ligne in texte.splitlines():
        normalisee = normaliser(ligne)
        for m in MONTANT.finditer(ligne):
            valeur = _nombre(m.group(1))
            prioritaire = any(mot in normalisee for mot in MOTS_TOTAL)
            cle = (prioritaire, valeur)
            if meilleur is None or cle > meilleur[0]:
                meilleur = (cle, valeur, m.group(0).strip())
    if meilleur is None:
        return None
    return {"valeur": meilleur[1], "texte": meilleur[2]}


def trouver_dates(texte):
    """Retourne la date de la facture et l'echeance (format AAAA-MM-JJ)."""
    date_facture = None
    echeance = None
    for ligne in texte.splitlines():
        normalisee = normaliser(ligne)
        for m in DATE.finditer(ligne):
            jour, mois, annee = m.groups()
            iso = "%s-%02d-%02d" % (annee, int(mois), int(jour))
            if any(mot in normalisee for mot in MOTS_ECHEANCE):
                echeance = echeance or iso
            else:
                date_facture = date_facture or iso
    return {"date": date_facture, "echeance": echeance}


def trouver_numero(texte):
    m = NUMERO.search(texte)
    return m.group(1) if m else None


def extraire(texte):
    dates = trouver_dates(texte)
    return {
        "numero": trouver_numero(texte),
        "montant": trouver_montant(texte),
        "date": dates["date"],
        "echeance": dates["echeance"],
    }
