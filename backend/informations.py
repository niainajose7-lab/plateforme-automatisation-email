"""Informations cles extraites d'un email, selon sa categorie."""
import html
import re
import unicodedata

from extraction import extraire

MOIS = "janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre"
JOURS = "lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche"
DATE_TEXTE = re.compile(r"\b(\d{1,2})(?:er)?\s+(" + MOIS + r")(?:\s+(\d{4}))?\b")
HEURE = re.compile(r"\b(\d{1,2})\s*(?:h|:)\s*(\d{2})?(?!\d)")
JOUR = re.compile(r"\b(" + JOURS + r")\b")
REF = r"\s*(?:n[o\xb0]?\.?|numero)?[\s:]*([0-9a-z][0-9a-z\-/]*\d)"
NUM_COMMANDE = re.compile(r"commande" + REF)
NUM_REFERENCE = re.compile(r"(?:commande|facture|ticket|dossier)" + REF)
POSTE = re.compile(r"poste\s+(?:de\s+|d')([^.,\n]{3,40})")


def _sans_accent(t):
    d = unicodedata.normalize("NFD", t)
    return "".join(c for c in d if unicodedata.category(c) != "Mn").lower()


def _texte(e):
    morceaux = [e.objet or "", html.unescape(e.corps or e.extrait or ""), e.texte_pj or ""]
    return "\n".join(morceaux)


def _date_proche(t, mots):
    for ligne in t.splitlines():
        if any(m in ligne for m in mots):
            m = DATE_TEXTE.search(ligne)
            if m:
                return m.group(0)
    return None


def _montant(texte):
    m = extraire(texte)["montant"]
    return m["texte"] if m else None


def _heure(t):
    m = HEURE.search(t)
    if not m:
        return None
    return "%sh%s" % (m.group(1), m.group(2) or "00")


def extraire_informations(categorie, e):
    code = _sans_accent(categorie or "")
    brut = _texte(e)
    t = _sans_accent(brut)
    ECH = ("avant le", "echeance", "date limite", "au plus tard")
    info = {}
    if "factur" in code:
        x = extraire(brut)
        info = {
            "numero": x["numero"],
            "montant": _montant(brut),
            "echeance": x["echeance"] or _date_proche(t, ECH),
        }
    elif "commande" in code:
        m = NUM_COMMANDE.search(t)
        info = {
            "numero": m.group(1) if m else None,
            "montant": _montant(brut),
            "livraison": _date_proche(t, ("livraison", "avant le", "pour le")),
        }
    elif "devis" in code:
        info = {
            "budget": _montant(brut),
            "delai": _date_proche(t, ("delai", "avant le", "pour le", "au plus tard")),
        }
    elif "reclam" in code:
        m = NUM_REFERENCE.search(t)
        info = {"reference": m.group(1) if m else None, "montant": _montant(brut)}
    elif "reunion" in code or "rendez" in code:
        j = JOUR.search(t)
        d = DATE_TEXTE.search(t)
        info = {
            "jour": j.group(1) if j else None,
            "date": d.group(0) if d else None,
            "heure": _heure(t),
        }
    elif "bourse" in code:
        info = {"echeance": _date_proche(t, ECH + ("jusqu",))}
    elif "support" in code:
        info = {"urgence": "urgent" if "urgent" in t else None}
    elif "candid" in code:
        m = POSTE.search(t)
        info = {"poste": m.group(1).strip() if m else None}
    return {k: v for k, v in info.items() if v}
