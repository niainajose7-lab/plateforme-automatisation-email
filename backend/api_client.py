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


