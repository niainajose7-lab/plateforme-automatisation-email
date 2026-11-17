import asyncio
import threading

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from sqlalchemy import or_, func

from database import SessionLocal
from models import BoiteMail, Email, Regle, Execution, PieceJointe, Action, Client, ExpediteurBloque, Alerte, Categorie
from gmail_service import (
    dechiffrer,
    credentials_depuis_refresh,
    lire_apercus,
    lister_pieces_jointes,
    telecharger_piece_jointe,
    transferer_email,
)
from extraction import extraire
from informations import extraire_informations
from systeme import message_systeme
from qualification import qualifier_marque
from notifications import envoyer_notifications
from intelligence import classer; from spam import detecter_spam
from ocr import lire_octets
from securite import detecter_danger, detecter_publicite
from moteur import evaluer

VERROU = threading.Lock()  # evite deux traitements en meme temps (boucle + bouton)
INTERVALLE = 60  # secondes entre deux passages
SEUIL_AUTO = 0.8  # en dessous, on demande une validation
TYPES_ACCEPTES = (
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "application/pdf",
)
TAILLE_MAX = 5 * 1024 * 1024  # 5 Mo


from email.utils import parseaddr, parsedate_to_datetime


def lire_date(texte):
    try:
        return parsedate_to_datetime(texte)
    except Exception:
        return None


def qualifier_expediteur(db, expediteur):
    """Identifie l'expediteur : client actif, desactive, bloque ou inconnu."""
    adresse = parseaddr(expediteur or "")[1].lower()
    if db.query(ExpediteurBloque).filter(ExpediteurBloque.adresse == adresse).first():
        return {"decision": "rejete", "motif": "adresse bloquee"}
    client = db.query(Client).filter(func.lower(Client.email) == adresse).first()
    if client is None:
        return {"decision": "inconnu", "motif": "expediteur inconnu"}
    if not client.actif:
        return {"client_id": client.id, "decision": "rejete", "motif": "client desactive"}
    return {"client_id": client.id}


def synchroniser_boite(db, boite):
    refresh = dechiffrer(boite.token_oauth)
    creds = credentials_depuis_refresh(refresh)
    apercus = lire_apercus(creds, max_results=30)

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
                date_reception=lire_date(a["date"]),
                **(message_systeme(a) or qualifier_marque(db, a, boite.adresse_email) or qualifier_expediteur(db, a["de"])),
            )
        )
        nouveaux += 1
    db.commit()
    return nouveaux


def traiter_pieces_jointes(db, boite):
    emails = (
        db.query(Email)
        .filter(
            Email.boite_mail_id == boite.id,
            or_(Email.pj_traitees.is_(None), Email.pj_traitees.is_(False)),
            or_(Email.decision.is_(None), Email.decision.notin_(('rejete', 'inconnu'))),
        )
        .all()
    )
    if not emails:
        return 0

    creds = credentials_depuis_refresh(dechiffrer(boite.token_oauth))
    lues = 0
    for e in emails:
        try:
            pieces = lister_pieces_jointes(creds, e.gmail_id)
        except HttpError as err:
            if err.resp.status == 404:
                # Email supprime dans Gmail : plus rien a lire, on n'insiste pas
                e.pj_traitees = True
                db.commit()
            else:
                print("[auto] pieces jointes :", type(err).__name__, err)
            continue
        except Exception as err:
            # Probleme reseau : on reessaiera au prochain passage
            print("[auto] pieces jointes :", type(err).__name__, err)
            continue

        textes = []
        for p in pieces:
            fiche = PieceJointe(
                email_id=e.id,
                nom=p["nom"],
                type_mime=p["type"],
                taille=p["taille"],
            )
            if p["type"] not in TYPES_ACCEPTES or p["taille"] > TAILLE_MAX:
                fiche.statut = "ignoree"
            else:
                try:
                    donnees = telecharger_piece_jointe(
                        creds, e.gmail_id, p["attachment_id"]
                    )
                    texte = lire_octets(donnees, p["type"], p["nom"])
                    fiche.texte = texte
                    fiche.donnees_extraites = extraire(texte)
                    fiche.statut = "lue"
                    textes.append(texte)
                    lues += 1
                except Exception as err:
                    fiche.statut = "erreur"
                    fiche.details_erreur = type(err).__name__ + " : " + str(err)
            db.add(fiche)

        e.texte_pj = "\n".join(textes) if textes else None
        e.pj_traitees = True
        db.commit()
    return lues


def donnees_pieces_jointes(db, email):
    fiches = (
        db.query(PieceJointe)
        .filter(PieceJointe.email_id == email.id, PieceJointe.statut == "lue")
        .all()
    )
    for f in fiches:
        if f.donnees_extraites:
            return f.donnees_extraites
    return None


def analyser_email(db, e):
    """Securite d'abord, puis publicite, puis spam, puis categorie."""
    noms = [p.nom for p in db.query(PieceJointe).filter(PieceJointe.email_id == e.id).all()]
    danger = detecter_danger(e, noms)
    if danger:
        e.categorie, e.confiance = "dangereux", 0.9
        e.decision, e.motif, e.traite = "bloque", danger[1], True
        db.add(Alerte(email_id=e.id, type=danger[0], details=danger[1]))
    elif detecter_publicite(e):
        e.categorie, e.confiance = "publicite", 0.9
        e.decision, e.motif, e.traite = "non_retenu", "publicite", True
    elif detecter_spam(e)[0]:
        e.categorie, e.confiance = "spam", 0.9
    else:
        e.categorie, e.confiance = classer(e)
    e.informations = extraire_informations(e.categorie, e)

def classer_emails(db, boite):
    emails = (
        db.query(Email)
        .filter(
            Email.boite_mail_id == boite.id,
            Email.categorie.is_(None),
            or_(Email.decision.is_(None), Email.decision.notin_(('rejete', 'inconnu'))),
        )
        .all()
    )
    for e in emails:
        analyser_email(db, e)
    db.commit()
    return len(emails)


def synchroniser_regles(db, boite):
    """Une regle par categorie, creee et mise a jour depuis la table categorie."""
    db.query(Regle).filter(
        Regle.boite_mail_id == boite.id, Regle.categorie_code.is_(None)
    ).update({"actif": False})
    for c in db.query(Categorie).all():
        regle = (
            db.query(Regle)
            .filter(Regle.boite_mail_id == boite.id, Regle.categorie_code == c.code)
            .first()
        )
        if regle is None and not c.service_email:
            continue
        if regle is None:
            regle = Regle(
                boite_mail_id=boite.id,
                nom="Categorie : " + c.nom,
                condition={"champ": "categorie", "operateur": "egal", "valeur": c.code},
                categorie_code=c.code,
            )
            db.add(regle)
            db.flush()
            db.add(Action(regle_id=regle.id, type_action="transferer", configuration={}))
        regle.seuil = c.seuil
        regle.actif = bool(c.actif and c.service_email)
        for a in db.query(Action).filter(Action.regle_id == regle.id).all():
            a.configuration = {"destinataire": c.service_email or ""}
    db.commit()


def appliquer_regles(db, boite):
    regles = (
        db.query(Regle)
        .filter(Regle.boite_mail_id == boite.id, Regle.actif.is_(True))
        .order_by(Regle.priorite.desc())
        .all()
    )
    # Seuls les emails pas encore decides sont examines
    emails = (
        db.query(Email)
        .filter(
            Email.boite_mail_id == boite.id,
            or_(Email.decision.is_(None), Email.decision == "en_attente"),
        )
        .all()
    )

    retenus = 0
    non_retenus = 0
    creds_cache = {}
    for e in emails:
        correspondance = None
        for regle in regles:
            if evaluer(regle.condition, e):
                correspondance = regle
                break  # une seule regle par email (la plus prioritaire)

        if correspondance is None:
            e.decision = "non_retenu"
            e.motif = 'categorie non prise en charge'
            e.traite = True
            non_retenus += 1
            continue

        # Regle basee sur la categorie : on verifie la confiance
        incertain = (
            correspondance.condition.get("champ") == "categorie"
            and (e.confiance or 0) < (correspondance.seuil or SEUIL_AUTO)
        )
        incertain = incertain or any((a.configuration or {}).get("validation") for a in db.query(Action).filter(Action.regle_id == correspondance.id).all())
        statut, details = "en_attente_validation", None
        if not incertain:
            statut, details = executer_actions(
                db, boite, correspondance, e, creds_cache
            )
        db.add(
            Execution(
                regle_id=correspondance.id,
                email_id=str(e.id),
                statut=statut,
                details_erreur=details,
                donnees_extraites={
                    "objet": e.objet,
                    "expediteur": e.expediteur,
                    "categorie": e.categorie,
                    "confiance": e.confiance,
                    "piece_jointe": donnees_pieces_jointes(db, e),
                },
            )
        )
        e.decision = "a_valider" if incertain else "retenu"
        e.motif = 'en attente de validation' if incertain else None
        e.traite = True
        retenus += 1
    db.commit()
    return retenus, non_retenus


def executer_actions(db, boite, regle, email, creds_cache):
    """Execute les actions de la regle. Retourne (statut, details)."""
    actions = (
        db.query(Action)
        .filter(Action.regle_id == regle.id)
        .order_by(Action.ordre_execution)
        .all()
    )
    for action in actions:
        if action.type_action != "transferer":
            continue
        dest = (action.configuration or {}).get("destinataire", "").strip()
        if not dest:
            return "echec", "destinataire manquant"
        # Anti-boucle : jamais vers sa propre boite, jamais un email deja transfere
        if dest.lower() == (boite.adresse_email or "").lower():
            return "ignore", "destinataire = la boite elle-meme"
        if (email.objet or "").lower().startswith(("[transfert]", "delivery status notification")) or "mailer-daemon" in (email.expediteur or "").lower() or "postmaster" in (email.expediteur or "").lower():
            return "ignore", "email deja transfere par la plateforme"
        try:
            if "creds" not in creds_cache:
                creds_cache["creds"] = credentials_depuis_refresh(
                    dechiffrer(boite.token_oauth)
                )
            transferer_email(creds_cache["creds"], email.gmail_id, dest, email.objet)
        except RefreshError:
            raise
        except Exception as err:
            return "echec", type(err).__name__ + " : " + str(err)
    return "succes", None


def traiter_boite(db, boite):
    """Un passage complet sur une boite : lecture, pieces jointes, classement, regles."""
    with VERROU:
        nouveaux = synchroniser_boite(db, boite)
        pj = traiter_pieces_jointes(db, boite)
        classes = classer_emails(db, boite)
        synchroniser_regles(db, boite)
        retenus, non_retenus = appliquer_regles(db, boite)
        envoyer_notifications(db, boite)
    return nouveaux, pj, classes, retenus, non_retenus


def cycle():
    db = SessionLocal()
    try:
        boites = (
            db.query(BoiteMail)
            .filter(BoiteMail.statut_connexion == "actif")
            .all()
        )
        for boite in boites:
            try:
                nouveaux, pj, classes, retenus, non_retenus = traiter_boite(db, boite)
                if nouveaux or pj or classes or retenus or non_retenus:
                    print(
                        "[auto]",
                        nouveaux, "nouveaux,",
                        pj, "pieces jointes lues,",
                        classes, "classes,",
                        retenus, "retenus,",
                        non_retenus, "non retenus",
                    )
            except RefreshError:
                # Google refuse le jeton (expire ou revoque) : inutile de
                # reessayer chaque minute, la boite doit etre reconnectee
                db.rollback()
                boite.statut_connexion = "expire"
                db.commit()
                print(
                    "[auto] boite", boite.adresse_email,
                    ": acces Gmail expire, reconnectez-la.",
                )
            except Exception as e:
                db.rollback()
                print("[auto] erreur :", type(e).__name__, e)
    finally:
        db.close()


async def boucle():
    print("[auto] automatisation demarree (toutes les", INTERVALLE, "s)")
    while True:
        try:
            await asyncio.to_thread(cycle)
        except Exception as e:
            print("[auto] erreur cycle :", type(e).__name__, e)
        await asyncio.sleep(INTERVALLE)


