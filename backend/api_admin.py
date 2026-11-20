"""Routes de l'interface administrateur : tableau de bord, suivi, lecture d'un
email, validation, categories, clients, expediteurs inconnus, alertes."""
import html
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from email.utils import parseaddr
from google.auth.exceptions import RefreshError

from database import SessionLocal
from models import (
    Utilisateur, BoiteMail, Email, PieceJointe, Execution, Client,
    Categorie, Alerte, ExpediteurBloque,
)
from security import decoder_access_token

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def admin_et_boite(authorization: str, db: Session):
    """Verifie le jeton, le role admin, et renvoie (utilisateur, boite)."""
    token = authorization.replace("Bearer ", "").strip()
    sub = decoder_access_token(token)
    if not sub:
        raise HTTPException(status_code=401, detail="Session invalide, reconnectez-vous")
    try:
        uid = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Session invalide, reconnectez-vous")
    user = db.query(Utilisateur).filter(Utilisateur.id == uid).first()
    if not user:
        raise HTTPException(status_code=401, detail="Session invalide, reconnectez-vous")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Reserve a l'administrateur")
    boite = db.query(BoiteMail).filter(BoiteMail.utilisateur_id == user.id).first()
    if not boite:
        raise HTTPException(status_code=404, detail="Aucune boite mail connectee")
    return user, boite


def date_de(e):
    d = e.date_reception or e.date_sync
    return d.isoformat() if d else None


def noms_clients(db, user):
    return {
        c.id: c
        for c in db.query(Client).filter(Client.proprietaire_id == user.id).all()
    }


# ---------------------------------------------------------------- tableau
@router.get("/tableau")
def tableau(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    user, boite = admin_et_boite(authorization, db)
    maintenant = datetime.now(timezone.utc)
    debut = (maintenant - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)

    tous = db.query(Email).filter(Email.boite_mail_id == boite.id, or_(Email.motif.is_(None), Email.motif.notin_(("copie systeme", "notification systeme")))).all()
    total = {"recus": len(tous), "retenus": 0, "non_retenus": 0,
             "a_valider": 0, "bloques": 0, "rejetes": 0, "inconnus": 0}
    cles = {"retenu": "retenus", "non_retenu": "non_retenus", "a_valider": "a_valider",
            "bloque": "bloques", "rejete": "rejetes", "inconnu": "inconnus"}
    par_jour = {}
    for i in range(7):
        j = (debut + timedelta(days=i)).date().isoformat()
        par_jour[j] = {"jour": j, "recus": 0, "retenus": 0}
    par_categorie = {}
    for e in tous:
        if e.decision in cles:
            total[cles[e.decision]] += 1
        d = e.date_reception or e.date_sync
        if d is not None:
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            j = d.date().isoformat()
            if j in par_jour:
                par_jour[j]["recus"] += 1
                if e.decision == "retenu":
                    par_jour[j]["retenus"] += 1
        if e.categorie and e.decision in ("retenu", "a_valider", "non_retenu"):
            par_categorie[e.categorie] = par_categorie.get(e.categorie, 0) + 1

    cats = {c.code: c.nom for c in db.query(Categorie).all()}
    categories = [
        {"code": k, "nom": cats.get(k, {"publicite": "Publicité", "dangereux": "Dangereux"}.get(k, k)), "nombre": v}
        for k, v in sorted(par_categorie.items(), key=lambda x: -x[1])
    ]

    recents = (
        db.query(Email).filter(Email.boite_mail_id == boite.id)
        .filter(or_(Email.motif.is_(None), Email.motif.notin_(("copie systeme", "notification systeme")))).order_by(Email.date_sync.desc()).limit(6).all()
    )
    clients = noms_clients(db, user)
    derniers = [
        {"id": str(e.id), "objet": e.objet, "categorie": e.categorie,
         "decision": e.decision, "date": date_de(e),
         "client": clients[e.client_id].nom if e.client_id in clients else None}
        for e in recents
    ]
    alertes = db.query(Alerte).filter(Alerte.traitee.is_(False)).count()
    return {"totaux": total, "par_jour": list(par_jour.values()),
            "par_categorie": categories, "derniers": derniers,
            "alertes_ouvertes": alertes}


# ------------------------------------------------------------------ suivi
@router.get("/emails")
def liste_emails(
    q: str = "", decision: str = "", categorie: str = "", client_id: str = "",
    debut: str = "", fin: str = "", page: int = 1, taille: int = 15,
    authorization: str = Header(default=""), db: Session = Depends(get_db),
):
    user, boite = admin_et_boite(authorization, db)
    req = db.query(Email).filter(Email.boite_mail_id == boite.id, or_(Email.motif.is_(None), Email.motif.notin_(("copie systeme", "notification systeme"))))
    if q:
        motif = "%" + q + "%"
        req = req.filter(or_(Email.objet.ilike(motif), Email.expediteur.ilike(motif)))
    if decision:
        req = req.filter(Email.decision == decision)
    if categorie:
        req = req.filter(Email.categorie == categorie)
    if client_id:
        try:
            req = req.filter(Email.client_id == uuid.UUID(client_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Client invalide")
    date_col = func.coalesce(Email.date_reception, Email.date_sync)
    try:
        if debut:
            req = req.filter(date_col >= datetime.fromisoformat(debut))
        if fin:
            req = req.filter(date_col < datetime.fromisoformat(fin) + timedelta(days=1))
    except ValueError:
        raise HTTPException(status_code=400, detail="Date invalide (AAAA-MM-JJ)")

    total = req.count()
    taille = max(1, min(taille, 100))
    page = max(1, page)
    lignes = req.order_by(date_col.desc()).offset((page - 1) * taille).limit(taille).all()
    clients = noms_clients(db, user)
    return {
        "total": total, "page": page, "taille": taille,
        "emails": [
            {"id": str(e.id), "date": date_de(e), "objet": e.objet,
             "expediteur": e.expediteur, "categorie": e.categorie,
             "confiance": e.confiance, "decision": e.decision, "motif": e.motif,
             "informations": e.informations,
             "client": clients[e.client_id].nom if e.client_id in clients else None}
            for e in lignes
        ],
    }


@router.get("/emails/{email_id}")
def detail_email(email_id: uuid.UUID, authorization: str = Header(default=""),
                 db: Session = Depends(get_db)):
    user, boite = admin_et_boite(authorization, db)
    e = db.query(Email).filter(Email.id == email_id, Email.boite_mail_id == boite.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Email introuvable")
    cat = db.query(Categorie).filter(Categorie.code == e.categorie).first()
    clients = noms_clients(db, user)
    pjs = db.query(PieceJointe).filter(PieceJointe.email_id == e.id).all()
    return {
        "id": str(e.id), "date": date_de(e), "objet": e.objet,
        "expediteur": e.expediteur, "corps": html.unescape(e.corps or e.extrait or ""),
        "categorie": e.categorie, "categorie_nom": cat.nom if cat else e.categorie,
        "confiance": e.confiance, "seuil": (cat.seuil if cat and cat.seuil else 0.8),
        "decision": e.decision, "motif": e.motif, "informations": e.informations,
        "client": clients[e.client_id].nom if e.client_id in clients else None,
        "pieces_jointes": [
            {"nom": p.nom, "type": p.type_mime, "statut": p.statut, "texte": p.texte}
            for p in pjs
        ],
    }


class Validation(BaseModel):
    accepter: bool
    motif: Optional[str] = None


@router.post("/emails/{email_id}/valider")
def valider(email_id: uuid.UUID, payload: Validation,
            authorization: str = Header(default=""), db: Session = Depends(get_db)):
    import automatisation

    user, boite = admin_et_boite(authorization, db)
    e = db.query(Email).filter(Email.id == email_id, Email.boite_mail_id == boite.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Email introuvable")
    if e.decision != "a_valider":
        raise HTTPException(status_code=409, detail="Cet email n'est pas a valider")
    ex = (
        db.query(Execution)
        .filter(Execution.email_id == str(e.id), Execution.statut == "en_attente_validation")
        .first()
    )
    if not ex:
        raise HTTPException(status_code=409, detail="Aucune action en attente")

    if not payload.accepter:
        if not (payload.motif or "").strip():
            raise HTTPException(status_code=400, detail="Indiquez un motif de refus")
        ex.statut = "refuse"
        ex.details_erreur = "Refuse par l'administrateur"
        e.decision = "non_retenu"
        e.motif = payload.motif.strip()
        db.commit()
        return {"decision": "non_retenu"}

    try:
        with automatisation.VERROU:
            statut, details = automatisation.executer_actions(db, boite, ex.regle, e, {})
    except RefreshError:
        db.rollback()
        boite.statut_connexion = "expire"
        db.commit()
        raise HTTPException(status_code=400, detail="Acces Gmail expire : reconnectez la boite")
    ex.statut = statut
    ex.details_erreur = details
    e.decision = "retenu"
    e.motif = None
    db.commit()
    return {"decision": "retenu", "statut": statut}


# ------------------------------------------------------------- categories
class CategorieModif(BaseModel):
    seuil: Optional[float] = None
    service_nom: Optional[str] = None
    service_email: Optional[str] = None
    actif: Optional[bool] = None


def vue_categorie(c):
    return {"id": str(c.id), "code": c.code, "nom": c.nom, "service_nom": c.service_nom,
            "service_email": c.service_email, "seuil": c.seuil, "actif": c.actif}


@router.get("/categories")
def liste_categories(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    admin_et_boite(authorization, db)
    return [vue_categorie(c) for c in db.query(Categorie).order_by(Categorie.ordre).all()]


@router.patch("/categories/{cat_id}")
def modifier_categorie(cat_id: uuid.UUID, p: CategorieModif,
                       authorization: str = Header(default=""), db: Session = Depends(get_db)):
    import automatisation

    user, boite = admin_et_boite(authorization, db)
    c = db.query(Categorie).filter(Categorie.id == cat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categorie introuvable")
    if p.seuil is not None:
        if not 0.3 <= p.seuil <= 0.99:
            raise HTTPException(status_code=400, detail="Seuil entre 0.30 et 0.99")
        c.seuil = p.seuil
    if p.service_nom is not None:
        c.service_nom = p.service_nom.strip()
    if p.service_email is not None:
        adresse = p.service_email.strip()
        if adresse and "@" not in parseaddr(adresse)[1]:
            raise HTTPException(status_code=400, detail="Adresse du service invalide")
        c.service_email = adresse
    if p.actif is not None:
        c.actif = p.actif
    db.commit()
    automatisation.synchroniser_regles(db, boite)
    return vue_categorie(c)


# ---------------------------------------------------------------- clients
class ClientNouveau(BaseModel):
    nom: str
    email: str


class ClientModif(BaseModel):
    nom: Optional[str] = None
    actif: Optional[bool] = None


def vue_client(db, c):
    nb = db.query(Email).filter(Email.client_id == c.id).count()
    return {"id": str(c.id), "identifiant": c.identifiant, "nom": c.nom,
            "email": c.email, "actif": c.actif, "nb_emails": nb}


def prochain_identifiant(db):
    n = db.query(Client).count() + 1
    while db.query(Client).filter(Client.identifiant == "CLI-%04d" % n).first():
        n += 1
    return "CLI-%04d" % n


@router.get("/clients")
def liste_clients(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    user, _ = admin_et_boite(authorization, db)
    cl = db.query(Client).filter(Client.proprietaire_id == user.id).order_by(Client.identifiant).all()
    return {"clients": [vue_client(db, c) for c in cl],
            "prochain_identifiant": prochain_identifiant(db)}


@router.post("/clients")
def creer_client(p: ClientNouveau, authorization: str = Header(default=""),
                 db: Session = Depends(get_db)):
    user, _ = admin_et_boite(authorization, db)
    adresse = parseaddr(p.email)[1].lower()
    if "@" not in adresse or not p.nom.strip():
        raise HTTPException(status_code=400, detail="Nom et adresse email valides requis")
    if db.query(Client).filter(func.lower(Client.email) == adresse).first():
        raise HTTPException(status_code=409, detail="Cette adresse est deja un client")
    c = Client(proprietaire_id=user.id, identifiant=prochain_identifiant(db),
               nom=p.nom.strip(), email=adresse, actif=True)
    db.add(c)
    db.commit()
    return vue_client(db, c)


@router.patch("/clients/{client_id}")
def modifier_client(client_id: uuid.UUID, p: ClientModif,
                    authorization: str = Header(default=""), db: Session = Depends(get_db)):
    user, _ = admin_et_boite(authorization, db)
    c = db.query(Client).filter(Client.id == client_id, Client.proprietaire_id == user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Client introuvable")
    if p.nom is not None and p.nom.strip():
        c.nom = p.nom.strip()
    if p.actif is not None:
        c.actif = p.actif
    db.commit()
    return vue_client(db, c)


# ------------------------------------------------------ expediteurs inconnus
class ActionInconnu(BaseModel):
    adresse: str
    action: str  # ignorer, ajouter, bloquer
    nom: Optional[str] = None


@router.get("/inconnus")
def liste_inconnus(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    _, boite = admin_et_boite(authorization, db)
    lignes = (
        db.query(Email).filter(Email.boite_mail_id == boite.id, Email.decision == "inconnu")
        .order_by(Email.date_sync.desc()).all()
    )
    vus = {}
    for e in lignes:
        a = parseaddr(e.expediteur or "")[1].lower()
        if a and a not in vus:
            vus[a] = {"adresse": a, "dernier_objet": e.objet, "nombre": 0}
        if a:
            vus[a]["nombre"] += 1
    return list(vus.values())


@router.post("/inconnus")
def agir_inconnu(p: ActionInconnu, authorization: str = Header(default=""),
                 db: Session = Depends(get_db)):
    user, boite = admin_et_boite(authorization, db)
    adresse = parseaddr(p.adresse)[1].lower()
    if not adresse:
        raise HTTPException(status_code=400, detail="Adresse invalide")
    emails = [
        e for e in db.query(Email).filter(
            Email.boite_mail_id == boite.id, Email.decision == "inconnu").all()
        if parseaddr(e.expediteur or "")[1].lower() == adresse
    ]
    if p.action == "ajouter":
        c = db.query(Client).filter(func.lower(Client.email) == adresse).first()
        if not c:
            c = Client(proprietaire_id=user.id, identifiant=prochain_identifiant(db),
                       nom=(p.nom or adresse.split("@")[0]).strip(), email=adresse, actif=True)
            db.add(c)
            db.flush()
        for e in emails:
            e.client_id = c.id
            e.decision = None
            e.motif = None
            e.traite = False
    elif p.action == "bloquer":
        if not db.query(ExpediteurBloque).filter(ExpediteurBloque.adresse == adresse).first():
            db.add(ExpediteurBloque(adresse=adresse))
        for e in emails:
            e.decision = "rejete"
            e.motif = "adresse bloquee"
    elif p.action == "ignorer":
        for e in emails:
            e.decision = "rejete"
            e.motif = "expediteur ignore"
    else:
        raise HTTPException(status_code=400, detail="Action inconnue")
    db.commit()
    return {"ok": True, "emails": len(emails)}


# ---------------------------------------------------------------- alertes
@router.get("/alertes")
def liste_alertes(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    admin_et_boite(authorization, db)
    res = []
    for a in db.query(Alerte).order_by(Alerte.date_creation.desc()).limit(50).all():
        e = db.query(Email).filter(Email.id == a.email_id).first() if a.email_id else None
        res.append({"id": str(a.id), "type": a.type, "details": a.details,
                    "traitee": a.traitee,
                    "date": a.date_creation.isoformat() if a.date_creation else None,
                    "objet": e.objet if e else None,
                    "expediteur": e.expediteur if e else None})
    return res


@router.post("/alertes/{alerte_id}/traiter")
def traiter_alerte(alerte_id: uuid.UUID, authorization: str = Header(default=""),
                   db: Session = Depends(get_db)):
    admin_et_boite(authorization, db)
    a = db.query(Alerte).filter(Alerte.id == alerte_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alerte introuvable")
    a.traitee = True
    db.commit()
    return {"ok": True}

