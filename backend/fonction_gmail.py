def envoyer_email(credentials, destinataire, objet, corps, piece=None):
    """Envoie un nouvel email depuis la boite connectee (piece = dict nom/type/donnees)."""
    service = build("gmail", "v1", credentials=credentials)
    msg = EmailMessage()
    msg["To"] = destinataire
    msg["Subject"] = " ".join((objet or "(sans objet)").split())  # une seule ligne
    msg.set_content(corps or "")
    if piece:
        maintype, _, subtype = (piece["type"] or "application/octet-stream").partition("/")
        msg.add_attachment(
            piece["donnees"],
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=piece["nom"],
        )
    brut = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    envoye = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": brut})
        .execute()
    )
    return envoye["id"]
