import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    Float,
    ForeignKey,
    DateTime,
    JSON,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Utilisateur(Base):
    __tablename__ = "utilisateur"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    mot_de_passe_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, server_default='admin')
    date_creation = Column(DateTime(timezone=True), server_default=func.now())

    boites_mail = relationship("BoiteMail", back_populates="utilisateur")
    connecteurs = relationship("Connecteur", back_populates="utilisateur")


class BoiteMail(Base):
    __tablename__ = "boite_mail"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utilisateur_id = Column(UUID(as_uuid=True), ForeignKey("utilisateur.id"), nullable=False)
    fournisseur = Column(String, nullable=False)  # gmail, outlook, imap
    adresse_email = Column(String)
    token_oauth = Column(Text)
    statut_connexion = Column(String, default="actif")
    date_connexion = Column(DateTime(timezone=True), server_default=func.now())

    utilisateur = relationship("Utilisateur", back_populates="boites_mail")
    regles = relationship("Regle", back_populates="boite_mail")
    emails = relationship("Email", back_populates="boite_mail")


class Email(Base):
    __tablename__ = "email"
    __table_args__ = (
        UniqueConstraint("boite_mail_id", "gmail_id", name="uq_email_boite_gmail"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    boite_mail_id = Column(UUID(as_uuid=True), ForeignKey("boite_mail.id"), nullable=False)
    gmail_id = Column(String, nullable=False)
    expediteur = Column(String)
    objet = Column(String)
    extrait = Column(Text)
    date_email = Column(String)
    date_sync = Column(DateTime(timezone=True), server_default=func.now())
    traite = Column(Boolean, default=False)
    categorie = Column(String)
    confiance = Column(Float)
    decision = Column(String, default="en_attente")
    pj_traitees = Column(Boolean, default=False)
    texte_pj = Column(Text)
    client_id = Column(UUID(as_uuid=True), ForeignKey('client.id'), nullable=True)
    corps = Column(Text)
    date_reception = Column(DateTime(timezone=True))
    motif = Column(Text)
    email_origine_id = Column(UUID(as_uuid=True), ForeignKey('email.id'), nullable=True)
    informations = Column(JSON)

    boite_mail = relationship("BoiteMail", back_populates="emails")
    pieces_jointes = relationship("PieceJointe", back_populates="email")


class PieceJointe(Base):
    __tablename__ = "piece_jointe"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(UUID(as_uuid=True), ForeignKey("email.id"), nullable=False)
    nom = Column(String)
    type_mime = Column(String)
    taille = Column(Integer)
    statut = Column(String, default="lue")  # lue, ignoree, erreur
    texte = Column(Text)
    donnees_extraites = Column(JSON)
    details_erreur = Column(Text)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())

    email = relationship("Email", back_populates="pieces_jointes")


class Regle(Base):
    __tablename__ = "regle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    boite_mail_id = Column(UUID(as_uuid=True), ForeignKey("boite_mail.id"), nullable=False)
    nom = Column(String, nullable=False)
    condition = Column(JSON, nullable=False)
    actif = Column(Boolean, default=True)
    priorite = Column(Integer, default=0)
    categorie_code = Column(String)
    seuil = Column(Float)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())

    boite_mail = relationship("BoiteMail", back_populates="regles")
    actions = relationship("Action", back_populates="regle")
    executions = relationship("Execution", back_populates="regle")


class Action(Base):
    __tablename__ = "action"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regle_id = Column(UUID(as_uuid=True), ForeignKey("regle.id"), nullable=False)
    connecteur_id = Column(UUID(as_uuid=True), ForeignKey("connecteur.id"), nullable=True)
    type_action = Column(String, nullable=False)
    configuration = Column(JSON)
    ordre_execution = Column(Integer, default=0)

    regle = relationship("Regle", back_populates="actions")
    connecteur = relationship("Connecteur", back_populates="actions")


class Execution(Base):
    __tablename__ = "execution"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regle_id = Column(UUID(as_uuid=True), ForeignKey("regle.id"), nullable=False)
    email_id = Column(String)
    statut = Column(String, nullable=False)  # succes, echec, en_attente_validation
    donnees_extraites = Column(JSON)
    details_erreur = Column(Text)
    date_execution = Column(DateTime(timezone=True), server_default=func.now())

    regle = relationship("Regle", back_populates="executions")


class Connecteur(Base):
    __tablename__ = "connecteur"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utilisateur_id = Column(UUID(as_uuid=True), ForeignKey("utilisateur.id"), nullable=False)
    type = Column(String, nullable=False)  # sheets, trello, slack, notion
    credentials = Column(Text)
    configuration = Column(JSON)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())

    utilisateur = relationship("Utilisateur", back_populates="connecteurs")
    actions = relationship("Action", back_populates="connecteur")


class Client(Base):
    __tablename__ = "client"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proprietaire_id = Column(UUID(as_uuid=True), ForeignKey("utilisateur.id"), nullable=False)
    utilisateur_id = Column(UUID(as_uuid=True), ForeignKey("utilisateur.id"), nullable=True)
    identifiant = Column(String, unique=True, nullable=False)
    nom = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    actif = Column(Boolean, nullable=False, default=True)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())


class Categorie(Base):
    __tablename__ = "categorie"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, nullable=False)
    nom = Column(String, nullable=False)
    service_nom = Column(String)
    service_email = Column(String)
    seuil = Column(Float, default=0.8)
    actif = Column(Boolean, default=True)
    ordre = Column(Integer, default=0)


class ExpediteurBloque(Base):
    __tablename__ = "expediteur_bloque"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    adresse = Column(String, unique=True, nullable=False)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())


class Alerte(Base):
    __tablename__ = "alerte"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(UUID(as_uuid=True), ForeignKey("email.id"), nullable=True)
    type = Column(String, nullable=False)
    details = Column(Text)
    traitee = Column(Boolean, default=False)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notification"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(UUID(as_uuid=True), ForeignKey("email.id"), nullable=False)
    type = Column(String, nullable=False)
    destinataire = Column(String)
    statut = Column(String, nullable=False)
    details = Column(Text)
    date_envoi = Column(DateTime(timezone=True), server_default=func.now())
