import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine
import auth
import emails
import regles
import api_admin
import automatisation


@asynccontextmanager
async def lifespan(app: FastAPI):
    tache = asyncio.create_task(automatisation.boucle())
    yield
    tache.cancel()


app = FastAPI(title="Plateforme email", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(emails.router)
app.include_router(regles.router)
app.include_router(api_admin.router)


@app.get("/")
def accueil():
    return {"statut": "backend operationnel"}


@app.get("/test-db")
def test_db():
    with engine.connect() as connexion:
        connexion.execute(text("SELECT 1"))
    return {"statut": "connexion PostgreSQL OK"}
