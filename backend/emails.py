import base64
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from database import SessionLocal
from models import BoiteMail, Email, PieceJointe, Execution, Regle, Action
from security import decoder_access_token
from gmail_service import (
    dechiffrer,
    credentials_depuis_refresh,
    lire_apercus,
    envoyer_email,
)

router = APIRouter(prefix="/emails", tags=["emails"])

MSG_SESSION = "Session invalide, reconnectez-vous"
MSG_BOITE = "Boite mail introuvable"
MSG_EXPIRE = "Acces Gmail expire : reconnectez la boite"
TAILLE_MAX_ENVOI = 5 * 1024 * 1024  # 5 Mo


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def utilisateur_depuis_header(authorization: str):
    token = authorization.replace("Bearer ", "").strip()
    sub = decoder_access_token(token)
    if not sub:
        raise HTTPException(status_code=401, detail=MSG_SESSION)
    try:
        return uuid.UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail=MSG_SESSION)


def trouver_boite(db, boite_id, utilisateur_id):
    boite = (
        db.query(BoiteMail)
        .filter(
            BoiteMail.id == boite_id,
            BoiteMail.utilisateur_id == utilisateur_id,
        )
        .first()
    )
    if not boite:
        raise HTTPException(status_code=404, detail=MSG_BOITE)
    return boite


def obtenir_credentials(db, boite):
    try:
        refresh = dechiffrer(boite.token_oauth)
        return credentials_depuis_refresh(refresh)
    except Exception as e:
        print("ERREUR LECTURE:", type(e).__name__, e)
        boite.statut_connexion = "expire"
        db.commit()
        raise HTTPException(status_code=400, detail=MSG_EXPIRE)


@router.get("/")
def lister_boites(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    utilisateur_id = utilisateur_depuis_header(authorization)
    boites = (
        db.query(BoiteMail)
        .filter(BoiteMail.utilisateur_id == utilisateur_id)
        .all()
    )
    return [
        {
            "id": str(b.id),
            "adresse": b.adresse_email,
            "statut": b.statut_connexion,
        }
        for b in boites
    ]


@router.get("/{boite_id}")
def lister_emails(
    boite_id: uuid.UUID,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    utilisateur_id = utilisateur_depuis_header(authorization)
    boite = trouver_boite(db, boite_id, utilisateur_id)
    creds = obtenir_credentials(db, boite)
    return lire_apercus(creds)


def resume_execution(db, email_id):
    """Derniere execution d'un email : regle appliquee et resultat."""
    ex = (
        db.query(Execution)
        .filter(Execution.email_id == str(email_id))
        .order_by(Execution.date_execution.desc())
        .first()
    )
    if not ex:
        return None
    regle = db.query(Regle).filter(Regle.id == ex.regle_id).first()
    action = (
        db.query(Action)
        .filter(Action.regle_id == ex.regle_id, Action.type_action == "transferer")
        .first()
    )
    conf = (action.configuration or {}) if action else {}
    dest = ", ".join(conf.get("destinataires") or []) or conf.get("destinataire")
    return {
        "regle": regle.nom if regle else "?",
        "statut": ex.statut,
        "details": ex.details_erreur,
        "destinataire": dest,
        "date": ex.date_execution.isoformat() if ex.date_execution else None,
    }


@router.get("/{boite_id}/historique")
def historique(
    boite_id: uuid.UUID,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Toutes les actions executees (ou en attente) sur les emails de la boite."""
    utilisateur_id = utilisateur_depuis_header(authorization)
    boite = trouver_boite(db, boite_id, utilisateur_id)
    emails = {
        str(e.id): e
        for e in db.query(Email).filter(Email.boite_mail_id == boite.id).all()
    }
    if not emails:
        return []
    executions = (
        db.query(Execution)
        .filter(Execution.email_id.in_(list(emails.keys())))
        .order_by(Execution.date_execution.desc())
        .limit(100)
        .all()
    )
    resultat = []
    for ex in executions:
        r = resume_execution(db, ex.email_id)
        e = emails[ex.email_id]
        resultat.append(
            {
                "date": ex.date_execution.isoformat() if ex.date_execution else None,
                "objet": e.objet,
                "expediteur": e.expediteur,
                "categorie": e.categorie,
                "regle": r["regle"] if r else "?",
                "statut": ex.statut,
                "details": ex.details_erreur,
                "destinataire": r["destinataire"] if r else None,
            }
        )
    return resultat


@router.get("/{boite_id}/suivi")
def suivi_emails(
    boite_id: uuid.UUID,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    utilisateur_id = utilisateur_depuis_header(authorization)
    boite = trouver_boite(db, boite_id, utilisateur_id)
    emails = (
        db.query(Email)
        .filter(Email.boite_mail_id == boite.id)
        .order_by(Email.date_sync.desc())
        .limit(50)
        .all()
    )
    resultat = []
    for x in emails:
        fiche = (
            db.query(PieceJointe)
            .filter(PieceJointe.email_id == x.id, PieceJointe.statut == "lue")
            .first()
        )
        resultat.append(
            {
                "id": str(x.id),
                "objet": x.objet,
                "expediteur": x.expediteur,
                "categorie": x.categorie,
                "confiance": x.confiance,
                "decision": x.decision,
                "facture": fiche.donnees_extraites if fiche else None,
                "execution": resume_execution(db, x.id),
            }
        )
    return resultat


@router.post("/{boite_id}/traiter")
def traiter_maintenant(
    boite_id: uuid.UUID,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Lance tout de suite un passage complet (sans attendre la boucle)."""
    import automatisation

    utilisateur_id = utilisateur_depuis_header(authorization)
    boite = trouver_boite(db, boite_id, utilisateur_id)
    try:
        nouveaux, pj, classes, retenus, non_retenus = automatisation.traiter_boite(db, boite)
    except RefreshError:
        db.rollback()
        boite.statut_connexion = "expire"
        db.commit()
        raise HTTPException(status_code=400, detail=MSG_EXPIRE)
    return {
        "nouveaux": nouveaux,
        "pieces_jointes_lues": pj,
        "classes": classes,
        "retenus": retenus,
        "non_retenus": non_retenus,
    }


@router.post("/{boite_id}/sync")
def synchroniser(
    boite_id: uuid.UUID,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    utilisateur_id = utilisateur_depuis_header(authorization)
    boite = trouver_boite(db, boite_id, utilisateur_id)
    creds = obtenir_credentials(db, boite)

    apercus = lire_apercus(creds, max_results=20)
    nouveaux = 0
    for a in apercus:
        existe = (
            db.query(Email)
            .filter(
                Email.boite_mail_id == boite.id,
                Email.gmail_id == a["id"],
            )
            .first()
        )
        if existe:
            continue
        db.add(
            Email(
                boite_mail_id=boite.id,
                gmail_id=a["id"],
                expediteur=a["de"],
                objet=a["objet"],
                extrait=a["extrait"],
                date_email=a["date"],
            )
        )
        nouveaux += 1
    db.commit()
    return {"lus": len(apercus), "nouveaux": nouveaux}


class PieceEnvoi(BaseModel):
    nom: str
    type: str = "application/octet-stream"
    donnees_base64: str


class MessageAEnvoyer(BaseModel):
    destinataire: EmailStr
    objet: str
    corps: str
    piece_jointe: Optional[PieceEnvoi] = None


@router.post("/{boite_id}/envoyer")
def envoyer(
    boite_id: uuid.UUID,
    payload: MessageAEnvoyer,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Envoie un email depuis la boite Gmail connectee."""
    utilisateur_id = utilisateur_depuis_header(authorization)
    boite = trouver_boite(db, boite_id, utilisateur_id)
    creds = obtenir_credentials(db, boite)

    piece = None
    if payload.piece_jointe:
        try:
            donnees = base64.b64decode(payload.piece_jointe.donnees_base64, validate=True)
        except Exception:
            raise HTTPException(status_code=400, detail="Piece jointe illisible")
        if len(donnees) > TAILLE_MAX_ENVOI:
            raise HTTPException(status_code=400, detail="Piece jointe trop volumineuse (5 Mo maximum)")
        piece = {
            "nom": payload.piece_jointe.nom,
            "type": payload.piece_jointe.type,
            "donnees": donnees,
        }

    try:
        gmail_id = envoyer_email(
            creds, str(payload.destinataire), payload.objet, payload.corps, piece
        )
    except HttpError as err:
        raise HTTPException(
            status_code=400,
            detail="Gmail a refuse l'envoi (code " + str(err.resp.status) + ")",
        )
    return {"envoye": True, "id": gmail_id}


class Validation(BaseModel):
    accepter: bool


@router.post("/{boite_id}/valider/{email_id}")
def valider_email(
    boite_id: uuid.UUID,
    email_id: uuid.UUID,
    payload: Validation,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Accepte ou refuse un email 'a valider' (decision humaine)."""
    import automatisation

    utilisateur_id = utilisateur_depuis_header(authorization)
    boite = trouver_boite(db, boite_id, utilisateur_id)
    email = (
        db.query(Email)
        .filter(Email.id == email_id, Email.boite_mail_id == boite.id)
        .first()
    )
    if not email:
        raise HTTPException(status_code=404, detail="Email introuvable")
    if email.decision != "a_valider":
        raise HTTPException(status_code=409, detail="Cet email n'est pas a valider")
    execution = (
        db.query(Execution)
        .filter(
            Execution.email_id == str(email.id),
            Execution.statut == "en_attente_validation",
        )
        .first()
    )
    if not execution:
        raise HTTPException(status_code=409, detail="Aucune action en attente")

    if not payload.accepter:
        execution.statut = "refuse"
        execution.details_erreur = "Refuse par l'utilisateur"
        email.decision = "non_retenu"
        db.commit()
        return {"decision": "non_retenu"}

    try:
        with automatisation.VERROU:
            statut, details = automatisation.executer_actions(
                db, boite, execution.regle, email, {}
            )
    except RefreshError:
        db.rollback()
        boite.statut_connexion = "expire"
        db.commit()
        raise HTTPException(status_code=400, detail=MSG_EXPIRE)
    execution.statut = statut
    execution.details_erreur = details
    email.decision = "retenu"
    db.commit()
    return {"decision": "retenu", "statut": statut}
