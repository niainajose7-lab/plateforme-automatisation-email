from email.utils import parseaddr


def message_systeme(a):
    """Renvoie un statut 'rejete' pour les messages generes par le systeme."""
    objet = (a.get("objet") or "").strip().lower()
    adresse = parseaddr(a.get("de") or "")[1].lower()
    if objet.startswith("[transfert]") or objet.startswith("[notification]"):
        return {"decision": "rejete", "motif": "copie systeme"}
    if (
        adresse.startswith("mailer-daemon")
        or adresse.startswith("postmaster")
        or "delivery status notification" in objet
    ):
        return {"decision": "rejete", "motif": "notification systeme"}
    return None
