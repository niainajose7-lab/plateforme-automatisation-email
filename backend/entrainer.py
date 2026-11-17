import csv
import json
import random

import torch
import torch.nn as nn

from modele_pytorch import CLASSES, Classifieur, jetons, texte_email, vecteur

random.seed(1)
torch.manual_seed(1)

# 1) Lecture des exemples d'entrainement
lignes = []
with open("train.csv", encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f, delimiter=";"):
        lignes.append(r)
random.shuffle(lignes)

# 2) Vocabulaire (mots vus au moins 2 fois)
compte = {}
for r in lignes:
    for m in set(jetons(texte_email(r["objet"], r["extrait"], r["expediteur"]))):
        compte[m] = compte.get(m, 0) + 1
vocab = {m: i for i, m in enumerate(sorted(m for m, n in compte.items() if n >= 2))}
print("Vocabulaire :", len(vocab), "mots")

X = torch.stack([vecteur(texte_email(r["objet"], r["extrait"], r["expediteur"]), vocab) for r in lignes])
y = torch.tensor([CLASSES.index(r["etiquette"]) for r in lignes])

# 3) Separation entrainement (80 %) / validation (20 %)
n_val = len(lignes) // 5
Xv, yv, Xt, yt = X[:n_val], y[:n_val], X[n_val:], y[n_val:]

modele = Classifieur(len(vocab))
opt = torch.optim.Adam(modele.parameters(), lr=0.01, weight_decay=1e-4)
perte = nn.CrossEntropyLoss()

for epoque in range(1, 61):
    modele.train()
    opt.zero_grad()
    l = perte(modele(Xt), yt)
    l.backward()
    opt.step()
    if epoque % 10 == 0:
        modele.eval()
        with torch.no_grad():
            acc = (modele(Xv).argmax(1) == yv).float().mean().item()
        print(f"epoque {epoque:2d}  perte {l.item():.3f}  precision validation {acc:.2%}")

torch.save(modele.state_dict(), "modele.pt")
with open("vocab.json", "w", encoding="utf-8") as f:
    json.dump(vocab, f, ensure_ascii=False)
print("Modele enregistre : modele.pt et vocab.json")
