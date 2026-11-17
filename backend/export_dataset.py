import csv
import os

from database import SessionLocal
from models import Email

# Reprend les etiquettes deja corrigees si l'ancien fichier existe
anciennes = {}
if os.path.exists("dataset_35.csv"):
    with open("dataset_35.csv", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            anciennes[r["id"]] = r["etiquette"]

db = SessionLocal()
emails = db.query(Email).order_by(Email.date_sync).all()

with open("dataset.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["id", "expediteur", "objet", "extrait", "categorie_auto", "etiquette", "texte_pj"])
    for e in emails:
        auto = e.categorie or "autre"
        w.writerow([
            str(e.id),
            e.expediteur or "",
            e.objet or "",
            (e.extrait or "").replace("\n", " ")[:300],
            auto,
            anciennes.get(str(e.id), auto),
            (e.texte_pj or "").replace("\n", " ")[:1500],
        ])

print("Emails exportes :", len(emails))
print("Etiquettes reprises :", sum(1 for e in emails if str(e.id) in anciennes))
db.close()
