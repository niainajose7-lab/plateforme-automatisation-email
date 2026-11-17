from datetime import datetime, timedelta, timezone
import os

from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", "change-moi-en-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_mot_de_passe(mot_de_passe: str) -> str:
    return pwd_context.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    return pwd_context.verify(mot_de_passe, hash_stocke)


def creer_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decoder_access_token(token: str):
    """Retourne l'identifiant utilisateur (sub) ou None si le token est invalide."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None