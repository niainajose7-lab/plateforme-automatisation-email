import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Utilisateur, BoiteMail
from schemas import (
    UtilisateurCreate,
    UtilisateurLogin,
    UtilisateurResponse,
    Token,
)
from security import (
    hash_mot_de_passe,
    verifier_mot_de_passe,
    creer_access_token,
    decoder_access_token,
)
from gmail_service import (
    generer_lien_autorisation,
    echanger_code_contre_token,
    lire_adresse,
    chiffrer,
)

router = APIRouter(prefix="/auth", tags=["auth"])

LIMITE_BOITES = 10

MSG_SESSION = "Session invalide, reconnectez-vous"
MSG_EMAIL_PRIS = "Cet email est deja utilise"
MSG_LOGIN = "Email ou mot de passe incorrect"
MSG_INTROUVABLE = "Utilisateur introuvable"
MSG_REFRESH = "Pas de refresh_token : reconnectez la boite Gmail"
MSG_LIMITE = "Limite de 10 boites mail atteinte"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=UtilisateurResponse)
def register(payload: UtilisateurCreate, db: Session = Depends(get_db)):
    existe = (
        db.query(Utilisateur)
        .filter(Utilisateur.email == payload.email)
        .first()
    )
    if existe:
        raise HTTPException(status_code=400, detail=MSG_EMAIL_PRIS)

    nouvel_utilisateur = Utilisateur(
        nom=payload.nom,
        email=payload.email,
        mot_de_passe_hash=hash_mot_de_passe(payload.mot_de_passe), role="client",
    )
    db.add(nouvel_utilisateur)
    db.commit()
    db.refresh(nouvel_utilisateur)
    return nouvel_utilisateur


@router.post("/login", response_model=Token)
def login(payload: UtilisateurLogin, db: Session = Depends(get_db)):
    utilisateur = (
        db.query(Utilisateur)
        .filter(Utilisateur.email == payload.email)
        .first()
    )
    if not utilisateur:
        raise HTTPException(status_code=401, detail=MSG_LOGIN)

    mdp_ok = verifier_mot_de_passe(
        payload.mot_de_passe, utilisateur.mot_de_passe_hash
    )
    if not mdp_ok:
        raise HTTPException(status_code=401, detail=MSG_LOGIN)

    token = creer_access_token({"sub": str(utilisateur.id)})
    return Token(access_token=token)


@router.get("/gmail/connect")
def connecter_gmail(token: str):
    # Le JWT passe dans "state" : Google le renvoie intact au retour
    if not decoder_access_token(token):
        raise HTTPException(status_code=401, detail=MSG_SESSION)
    url = generer_lien_autorisation(state=token)
    return RedirectResponse(url)


@router.get("/gmail/callback")
def callback_gmail(code: str, state: str, db: Session = Depends(get_db)):
    # 1. Retrouver l'utilisateur grace au state
    sub = decoder_access_token(state)
    if not sub:
        raise HTTPException(status_code=401, detail=MSG_SESSION)

    try:
        utilisateur_id = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail=MSG_SESSION)

    utilisateur = (
        db.query(Utilisateur)
        .filter(Utilisateur.id == utilisateur_id)
        .first()
    )
    if not utilisateur:
        raise HTTPException(status_code=401, detail=MSG_INTROUVABLE)

    # 2. Echanger le code contre les tokens
    creds = echanger_code_contre_token(code)
    if not creds.refresh_token:
        raise HTTPException(status_code=400, detail=MSG_REFRESH)

    adresse = lire_adresse(creds)
    refresh = creds.refresh_token
    token_chiffre = chiffrer(refresh)

    # 3. Boite deja connectee ? On met a jour le token
    boite = (
        db.query(BoiteMail)
        .filter(
            BoiteMail.utilisateur_id == utilisateur.id,
            BoiteMail.adresse_email == adresse,
        )
        .first()
    )
    if boite:
        boite.token_oauth = token_chiffre
        boite.statut_connexion = "actif"
        db.commit()
        return {"statut": "Boite Gmail mise a jour", "adresse": adresse}

    # 4. Limite de 10 boites
    nombre = (
        db.query(BoiteMail)
        .filter(BoiteMail.utilisateur_id == utilisateur.id)
        .count()
    )
    if nombre >= LIMITE_BOITES:
        raise HTTPException(status_code=400, detail=MSG_LIMITE)

    # 5. Creer la boite (aucun token n'est renvoye au navigateur)
    nouvelle_boite = BoiteMail(
        utilisateur_id=utilisateur.id,
        fournisseur="gmail",
        adresse_email=adresse,
        token_oauth=token_chiffre,
        statut_connexion="actif",
    )
    db.add(nouvelle_boite)
    db.commit()
    return {"statut": "Boite Gmail connectee", "adresse": adresse}
