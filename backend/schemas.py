from pydantic import BaseModel, EmailStr
import uuid


class UtilisateurCreate(BaseModel):
    nom: str
    email: EmailStr
    mot_de_passe: str


class UtilisateurLogin(BaseModel):
    email: EmailStr
    mot_de_passe: str


class UtilisateurResponse(BaseModel):
    id: uuid.UUID
    nom: str
    email: EmailStr

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"