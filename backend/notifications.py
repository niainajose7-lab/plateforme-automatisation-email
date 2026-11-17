"""Notifications automatiques envoyees aux clients par email."""
from models import Email, Client, Categorie, Notification
from gmail_service import dechiffrer, credentials_depuis_refresh, envoyer_email

TYPES = ("retenu", "non_retenu", "a_valider", "bloque")
LIBELLES = {
    "retenu": "retenu",
    "non_retenu": "non retenu",
    "a_valider": "en cours de validation",
    "bloque": "bloqué",
}


def _objet_propre(objet):
    o = (objet or "(sans objet)").strip()
    for marque in ("[Transfert]", "[Notification]"):
        if o.startswith(marque):
            o = o[len(marque):].strip()
    return o


def _corps(e, client, cat):
    objet = _objet_propre(e.objet)
    lignes = ["Bonjour " + client.nom + ",", ""]
    if e.decision == "retenu":
        service = (cat.service_nom if cat and cat.service_nom else "le service concerné")
        lignes.append("Votre email « " + objet + " » a été retenu et transmis à : " + service + ".")
        if cat:
            lignes.append("Catégorie : " + cat.nom)
        infos = e.informations if isinstance(e.informations, dict) else {}
        for cle, valeur in infos.items():
            if valeur and not isinstance(valeur, (dict, list)):
                lignes.append(cle.capitalize() + " : " + str(valeur))
    elif e.decision == "non_retenu":
        lignes.append("Votre email « " + objet + " » n'a pas été retenu.")
        lignes.append("Motif : " + (e.motif or "non précisé"))
        lignes.append("Vous pouvez corriger votre demande et la renvoyer.")
    elif e.decision == "a_valider":
        lignes.append("Votre email « " + objet + " » a bien été reçu.")
        lignes.append("Il est en cours de validation par l'administrateur.")
    else:
        lignes.append("Votre email « " + objet + " » a été bloqué par mesure de sécurité.")
        lignes.append("Si vous pensez à une erreur, contactez l'administrateur.")
    lignes += ["", "Cordialement,", "La plateforme AutoMail", "", "(Message automatique, merci de ne pas répondre.)"]
    return "\n".join(lignes)


def envoyer_notifications(db, boite):
    """Envoie une notification par decision, aux clients actifs. Ne leve jamais d'erreur."""
    envoyes = 0
    try:
        emails = (
            db.query(Email)
            .filter(
                Email.boite_mail_id == boite.id,
                Email.client_id.isnot(None),
                Email.decision.in_(TYPES),
            )
            .all()
        )
        creds = None
        for e in emails:
            deja = (
                db.query(Notification)
                .filter(Notification.email_id == e.id, Notification.type == e.decision)
                .first()
            )
            if deja:
                continue
            client = db.query(Client).filter(Client.id == e.client_id).first()
            if not client or not client.actif:
                continue
            cat = db.query(Categorie).filter(Categorie.code == e.categorie).first()
            sujet = "[Notification] " + _objet_propre(e.objet) + " : " + LIBELLES[e.decision]
            try:
                if creds is None:
                    creds = credentials_depuis_refresh(dechiffrer(boite.token_oauth))
                envoyer_email(creds, client.email, sujet, _corps(e, client, cat))
                statut, details = "envoye", None
            except Exception as err:
                statut, details = "echec", str(err)[:300]
                print("[notification] echec:", type(err).__name__, err)
            db.add(Notification(email_id=e.id, type=e.decision, destinataire=client.email, statut=statut, details=details))
            db.commit()
            envoyes += 1
    except Exception as err:
        db.rollback()
        print("[notification] erreur:", type(err).__name__, err)
    return envoyes
