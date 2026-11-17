import re
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from models import BoiteMail, Email, Regle, Execution, Action
from emails import get_db, utilisateur_depuis_header, trouver_boite
from moteur import evaluer

router = APIRouter(prefix="/regles", tags=["regles"])

MSG_REGLE = "Regle introuvable"


class Condition(BaseModel):
    champ: Literal["objet", "expediteur", "extrait", "categorie"]
    operateur: Literal["contient", "egal", "commence_par"]
    valeur: str


class RegleCreate(BaseModel):
    boite_mail_id: uuid.UUID
    nom: str
    condition: Condition
    transfert_vers: Optional[str] = None  # une ou plusieurs adresses separees par , ou ;
    validation: bool = False


def trouver_regle(db, regle_id, utilisateur_id):
    regle = (
        db.query(Regle)
        .join(BoiteMail, Regle.boite_mail_id == BoiteMail.id)
        .filter(
            Regle.id == regle_id,
            BoiteMail.utilisateur_id == utilisateur_id,
        )
        .first()
    )
    if not regle:
        raise HTTPException(status_code=404, detail=MSG_REGLE)
    return regle


def rouvrir_non_retenus(db, boite_id):
    """Un email 'non retenu' (aucune regle) est examine a nouveau quand une
    regle est creee ou activee. Les emails deja traites par une regle ne bougent pas."""
    deja = {
        x[0] for x in db.query(Execution.email_id).all()
    }
    emails = (
        db.query(Email)
        .filter(Email.boite_mail_id == boite_id, Email.decision == "non_retenu")
        .all()
    )
    for e in emails:
        if str(e.id) not in deja:
            e.decision = "en_attente"
            e.traite = False


_EMAIL = TypeAdapter(EmailStr)


def lire_adresses(texte):
    """Transforme 'a@x.com, b@y.com' en liste validee (sans doublons)."""
    adresses = []
    for morceau in re.split(r"[,;\s]+", texte or ""):
        morceau = morceau.strip()
        if not morceau:
            continue
        try:
            adresse = str(_EMAIL.validate_python(morceau))
        except ValidationError:
            raise HTTPException(status_code=422, detail="Adresse invalide : " + morceau)
        if adresse.lower() not in [a.lower() for a in adresses]:
            adresses.append(adresse)
    if len(adresses) > 20:
        raise HTTPException(status_code=422, detail="20 destinataires maximum par regle")
    return adresses


def destinataire_de(db, regle_id):
    action = (
        db.query(Action)
        .filter(Action.regle_id == regle_id, Action.type_action == "transferer")
        .first()
    )
    if action and action.configuration:
        liste = action.configuration.get("destinataires")
        if liste:
            return ", ".join(liste)
        return action.configuration.get("destinataire")
    return None


@router.post("/")
def creer_regle(
    payload: RegleCreate,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    utilisateur_id = utilisateur_depuis_header(authorization)
    boite = trouver_boite(db, payload.boite_mail_id, utilisateur_id)

    adresses = lire_adresses(payload.transfert_vers)
    regle = Regle(
        boite_mail_id=boite.id,
        nom=payload.nom,
        condition=payload.condition.model_dump(),
    )
    db.add(regle)
    db.flush()
    if adresses:
        db.add(
            Action(
                regle_id=regle.id,
                type_action="transferer",
                configuration={
                    "destinataire": adresses[0],
                    "destinataires": adresses,
                    "validation": payload.validation,
                },
            )
        )
    rouvrir_non_retenus(db, boite.id)
    db.commit()
    db.refresh(regle)
    return {
        "id": str(regle.id),
        "nom": regle.nom,
        "condition": regle.condition,
        "transfert_vers": ", ".join(adresses) or None,
    }


@router.get("/")
def lister_regles(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    utilisateur_id = utilisateur_depuis_header(authorization)
    regles = (
        db.query(Regle)
        .join(BoiteMail, Regle.boite_mail_id == BoiteMail.id)
        .filter(BoiteMail.utilisateur_id == utilisateur_id)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "nom": r.nom,
            "actif": r.actif,
            "condition": r.condition,
            "transfert_vers": destinataire_de(db, r.id),
            "validation": any((a.configuration or {}).get("validation") for a in db.query(Action).filter(Action.regle_id == r.id).all()),
        }
        for r in regles
    ]


class Activation(BaseModel):
    actif: bool


@router.patch("/{regle_id}")
def changer_etat(
    regle_id: uuid.UUID,
    payload: Activation,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    utilisateur_id = utilisateur_depuis_header(authorization)
    regle = trouver_regle(db, regle_id, utilisateur_id)
    regle.actif = payload.actif
    if payload.actif:
        rouvrir_non_retenus(db, regle.boite_mail_id)
    db.commit()
    return {"id": str(regle.id), "actif": regle.actif}


@router.delete("/{regle_id}")
def supprimer_regle(
    regle_id: uuid.UUID,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    utilisateur_id = utilisateur_depuis_header(authorization)
    regle = trouver_regle(db, regle_id, utilisateur_id)
    deja_agi = db.query(Execution).filter(Execution.regle_id == regle.id).first()
    if deja_agi:
        raise HTTPException(
            status_code=409,
            detail="Cette regle a deja agi sur des emails : desactivez-la plutot que de la supprimer.",
        )
    db.query(Action).filter(Action.regle_id == regle.id).delete()
    db.delete(regle)
    db.commit()
    return {"supprimee": True}


@router.post("/{regle_id}/appliquer")
def appliquer_regle(
    regle_id: uuid.UUID,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    utilisateur_id = utilisateur_depuis_header(authorization)
    regle = trouver_regle(db, regle_id, utilisateur_id)

    emails = (
        db.query(Email)
        .filter(
            Email.boite_mail_id == regle.boite_mail_id,
            Email.traite == False,  # noqa: E712
        )
        .all()
    )

    correspondants = []
    for e in emails:
        if evaluer(regle.condition, e):
            db.add(
                Execution(
                    regle_id=regle.id,
                    email_id=str(e.id),
                    statut="succes",
                    donnees_extraites={
                        "objet": e.objet,
                        "expediteur": e.expediteur,
                    },
                )
            )
            e.traite = True
            correspondants.append(e.objet)
    db.commit()

    return {
        "regle": regle.nom,
        "emails_examines": len(emails),
        "correspondants": len(correspondants),
        "objets": correspondants,
    }
