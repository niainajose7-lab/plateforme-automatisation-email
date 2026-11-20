"""Routes de l'espace client : identite, envoi d'un email, liste de ses emails,
creation de l'acces (par l'administrateur)."""
import base64
import uuid
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi import APIRouter, Depends, Header as EnteteHttp, HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Utilisateur, BoiteMail, Email, Client, Categorie
from security import decoder_access_token, hash_mot_de_passe
from gmail_service import dechiffrer, credentials_depuis_refresh

router = APIRouter(prefix="/client", tags=["client"])

MSG_SESSION = "Session invalide, reconnectez-vous"
TAILLE_MAX = 5 * 1024 * 1024  # 5 Mo


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def utilisateur_connecte(authorization: str, db: Session):
    token = authorization.replace("Bearer ", "").strip()
    sub = decoder_access_token(token)
    if not sub:
        raise HTTPException(status_code=401, detail=MSG_SESSION)
    try:
        uid = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail=MSG_SESSION)
    user = db.query(Utilisateur).filter(Utilisateur.id == uid).first()
    if not user:
        raise HTTPException(status_code=401, detail=MSG_SESSION)
    return user


def client_connecte(authorization: str, db: Session):
    user = utilisateur_connecte(authorization, db)
    client = db.query(Client).filter(Client.utilisateur_id == user.id).first()
    if user.role != "client" or client is None:
        raise HTTPException(status_code=403, detail="Compte client introuvable")
    return user, client


@router.get("/moi")
def moi(authorization: str = EnteteHttp(default=""), db: Session = Depends(get_db)):
    user = utilisateur_connecte(authorization, db)
    res = {"role": user.role, "nom": user.nom, "email": user.email}
    if user.role == "client":
        client = db.query(Client).filter(Client.utilisateur_id == user.id).first()
        if client:
            res.update({"identifiant": client.identifiant, "actif": client.actif, "nom": client.nom})
        else:
            res.update({"identifiant": None, "actif": False})
    return res


@router.get("/emails")
def mes_emails(authorization: str = EnteteHttp(default=""), db: Session = Depends(get_db)):
    user, client = client_connecte(authorization, db)
    cats = {c.code: c.nom for c in db.query(Categorie).all()}
    lignes = (
        db.query(Email).filter(Email.client_id == client.id)
        .order_by(Email.date_sync.desc()).limit(50).all()
    )
    res = []
    for e in lignes:
        d = e.date_reception or e.date_sync
        res.append({
            "id": str(e.id), "objet": e.objet, "date": d.isoformat() if d else None,
            "categorie": cats.get(e.categorie, e.categorie), "decision": e.decision,
            "motif": e.motif,
        })
    return res


class PieceEnvoi(BaseModel):
    nom: str
    type: str = "application/octet-stream"
    donnees_base64: str


class MessageClient(BaseModel):
    objet: str
    corps: str
    piece_jointe: Optional[PieceEnvoi] = None


@router.post("/envoyer")
def envoyer(payload: MessageClient, authorization: str = EnteteHttp(default=""),
            db: Session = Depends(get_db)):
    user, client = client_connecte(authorization, db)
    if not client.actif:
        raise HTTPException(status_code=403, detail="Votre compte est desactive")
    if not payload.objet.strip() or not payload.corps.strip():
        raise HTTPException(status_code=400, detail="Objet et message obligatoires")
    boite = db.query(BoiteMail).filter(BoiteMail.utilisateur_id == client.proprietaire_id).first()
    if not boite:
        raise HTTPException(status_code=503, detail="La plateforme n'est pas disponible")

    msg = MIMEMultipart()
    msg["To"] = boite.adresse_email
    msg["Subject"] = Header(payload.objet.strip(), "utf-8")
    msg["Reply-To"] = client.email
    msg["X-AutoMail-Client"] = client.identifiant
    msg.attach(MIMEText(payload.corps, "plain", "utf-8"))

    if payload.piece_jointe:
        try:
            donnees = base64.b64decode(payload.piece_jointe.donnees_base64, validate=True)
        except Exception:
            raise HTTPException(status_code=400, detail="Piece jointe illisible")
        if len(donnees) > TAILLE_MAX:
            raise HTTPException(status_code=400, detail="Piece jointe trop volumineuse (5 Mo maximum)")
        genre, _, sous = (payload.piece_jointe.type or "").partition("/")
        if not genre or not sous:
            genre, sous = "application", "octet-stream"
        partie = MIMEBase(genre, sous)
        partie.set_payload(donnees)
        encoders.encode_base64(partie)
        partie.add_header("Content-Disposition", "attachment", filename=payload.piece_jointe.nom)
        msg.attach(partie)

    try:
        creds = credentials_depuis_refresh(dechiffrer(boite.token_oauth))
        service = build("gmail", "v1", credentials=creds)
        brut = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": brut}).execute()
    except (RefreshError, HttpError):
        raise HTTPException(status_code=502, detail="Envoi impossible pour le moment, reessayez plus tard")
    return {"envoye": True}


class CreationAcces(BaseModel):
    client_id: uuid.UUID
    mot_de_passe: str


@router.post("/comptes")
def creer_acces(payload: CreationAcces, authorization: str = EnteteHttp(default=""),
                db: Session = Depends(get_db)):
    """L'administrateur cree (ou remet a zero) l'acces d'un client."""
    admin = utilisateur_connecte(authorization, db)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Reserve a l'administrateur")
    client = (
        db.query(Client)
        .filter(Client.id == payload.client_id, Client.proprietaire_id == admin.id).first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")
    if len(payload.mot_de_passe) < 6:
        raise HTTPException(status_code=400, detail="Mot de passe : 6 caracteres minimum")

    compte = None
    if client.utilisateur_id:
        compte = db.query(Utilisateur).filter(Utilisateur.id == client.utilisateur_id).first()
    if compte is None:
        existant = db.query(Utilisateur).filter(Utilisateur.email == client.email).first()
        if existant is not None:
            raise HTTPException(
                status_code=409,
                detail="Cette adresse est deja utilisee par un autre compte",
            )
        compte = Utilisateur(nom=client.nom, email=client.email, role="client",
                             mot_de_passe_hash=hash_mot_de_passe(payload.mot_de_passe))
        db.add(compte)
        db.flush()
        client.utilisateur_id = compte.id
    else:
        compte.mot_de_passe_hash = hash_mot_de_passe(payload.mot_de_passe)
    db.commit()
    return {"ok": True, "identifiant": client.identifiant, "email": client.email}
