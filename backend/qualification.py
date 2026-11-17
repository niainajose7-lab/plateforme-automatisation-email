from email.utils import parseaddr

from models import Client


def qualifier_marque(db, a, adresse_boite):
    """Email envoye depuis l'espace client : le client est lu dans l'en-tete
    X-AutoMail-Client. Accepte seulement si l'email vient de la boite de la plateforme."""
    ref = (a.get("client_ref") or "").strip()
    if not ref:
        return None
    de = parseaddr(a.get("de") or "")[1].lower()
    if de != (adresse_boite or "").lower():
        return None
    client = db.query(Client).filter(Client.identifiant == ref).first()
    if client is None:
        return None
    if not client.actif:
        return {"client_id": client.id, "decision": "rejete", "motif": "client desactive"}
    return {"client_id": client.id}
