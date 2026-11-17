from email.message import EmailMessage
import base64
import os

# Developpement local uniquement : a retirer en production (https requis)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from dotenv import load_dotenv
from cryptography.fernet import Fernet
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _env(nom):
    return os.getenv(nom, "").strip()


def _config_client():
    return {
        "web": {
            "client_id": _env("GOOGLE_CLIENT_ID"),
            "client_secret": _env("GOOGLE_CLIENT_SECRET"),
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": [_env("GOOGLE_REDIRECT_URI")],
        }
    }


def creer_flow():
    # Le Flow est recree a chaque requete : on desactive PKCE
    return Flow.from_client_config(
        _config_client(),
        scopes=SCOPES,
        redirect_uri=_env("GOOGLE_REDIRECT_URI"),
        autogenerate_code_verifier=False,
    )


def generer_lien_autorisation(state: str):
    flow = creer_flow()
    url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
    )
    return url


def echanger_code_contre_token(code: str):
    flow = creer_flow()
    flow.fetch_token(code=code)
    return flow.credentials


def lire_adresse(credentials: Credentials) -> str:
    service = build("gmail", "v1", credentials=credentials)
    profil = service.users().getProfile(userId="me").execute()
    return profil["emailAddress"]


def lister_emails(credentials: Credentials, max_results=5):
    service = build("gmail", "v1", credentials=credentials)
    resultats = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results)
        .execute()
    )
    return resultats.get("messages", [])


# --- Chiffrement du refresh_token ---

def _fernet() -> Fernet:
    return Fernet(_env("ENCRYPTION_KEY").encode())


def chiffrer(texte: str) -> str:
    return _fernet().encrypt(texte.encode()).decode()


def dechiffrer(texte_chiffre: str) -> str:
    return _fernet().decrypt(texte_chiffre.encode()).decode()


# --- Etape 11 : lecture des emails ---

def credentials_depuis_refresh(refresh_token: str):
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=_env("GOOGLE_CLIENT_ID"),
        client_secret=_env("GOOGLE_CLIENT_SECRET"),
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def lire_apercus(credentials, max_results=5):
    service = build("gmail", "v1", credentials=credentials)
    liste = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results)
        .execute()
        .get("messages", [])
    )
    apercus = []
    for m in liste:
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=m["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date", "X-AutoMail-Client"],
            )
            .execute()
        )
        h = {x["name"]: x["value"] for x in msg["payload"]["headers"]}
        apercus.append(
            {
                "id": m["id"],
                "de": h.get("From", ""),
                "objet": h.get("Subject", ""),
                "date": h.get("Date", ""),
                "extrait": msg.get("snippet", ""), "client_ref": h.get("X-AutoMail-Client", ""),
            }
        )
    return apercus


# --- Pieces jointes ---

def lister_pieces_jointes(credentials, gmail_id):
    service = build("gmail", "v1", credentials=credentials)
    message = (
        service.users()
        .messages()
        .get(userId="me", id=gmail_id, format="full")
        .execute()
    )
    pieces = []

    def parcourir(partie):
        for sous_partie in partie.get("parts", []) or []:
            parcourir(sous_partie)
        nom = partie.get("filename")
        corps = partie.get("body", {}) or {}
        if nom and corps.get("attachmentId"):
            pieces.append(
                {
                    "nom": nom,
                    "type": partie.get("mimeType", ""),
                    "taille": corps.get("size", 0),
                    "attachment_id": corps["attachmentId"],
                }
            )

    parcourir(message.get("payload", {}))
    return pieces


def telecharger_piece_jointe(credentials, gmail_id, attachment_id):
    service = build("gmail", "v1", credentials=credentials)
    pj = (
        service.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=gmail_id, id=attachment_id)
        .execute()
    )
    return base64.urlsafe_b64decode(pj["data"])
def transferer_email(credentials, gmail_id, destinataire, objet):
    """Envoie a `destinataire` un nouvel email contenant l'original en piece jointe (.eml)."""
    service = build("gmail", "v1", credentials=credentials)
    brut = (
        service.users()
        .messages()
        .get(userId="me", id=gmail_id, format="raw")
        .execute()
    )
    original = base64.urlsafe_b64decode(brut["raw"] + "==")

    sujet = " ".join((objet or "(sans objet)").split())  # une seule ligne
    msg = EmailMessage()
    msg["To"] = destinataire
    msg["Subject"] = "[Transfert] " + sujet
    msg["X-Plateforme-Transfert"] = "1"
    msg.set_content(
        "Email transfere automatiquement par la plateforme.\n"
        "Le message original est en piece jointe (original.eml)."
    )
    msg.add_attachment(
        original, maintype="message", subtype="rfc822", filename="original.eml"
    )
    corps = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    envoye = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": corps})
        .execute()
    )
    return envoye["id"]

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
