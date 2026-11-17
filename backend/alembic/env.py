import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from dotenv import load_dotenv

from alembic import context

# --- Ajouts spécifiques au projet ---
# Permet d'importer database.py et models.py depuis le dossier parent (backend/)
sys.path.append(os.getcwd())
load_dotenv()

from database import Base
from models import Utilisateur, BoiteMail, Regle, Action, Execution, Connecteur
# --- Fin des ajouts ---

# Objet de configuration Alembic, qui donne accès aux valeurs
# du fichier .ini en cours d'utilisation.
config = context.config

# Interprète le fichier de config pour le logging Python.
# Cette ligne configure essentiellement les loggers.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Récupère l'URL de connexion depuis le .env plutôt que depuis alembic.ini
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Objet MetaData de vos modèles, pour le support de l'autogénération
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Exécute les migrations en mode 'offline'.

    Configure le contexte uniquement avec une URL,
    sans créer d'Engine (une connexion DBAPI n'est même pas nécessaire ici).
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Exécute les migrations en mode 'online'.

    Dans ce cas, on crée un Engine et on y associe une connexion.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()