"""Compare le score a poids et PyTorch sur les VRAIS emails etiquetes (dataset.csv)."""
import csv
import sys
import time
from types import SimpleNamespace

from intelligence import classer_poids
from modele_pytorch import CLASSES, charger, predire

fichier = sys.argv[1] if len(sys.argv) > 1 else "dataset.csv"
with open(fichier, encoding="utf-8-sig", newline="") as f:
    lignes = list(csv.DictReader(f, delimiter=";"))
lignes = [r for r in lignes if r.get("etiquette")]
print(f"{len(lignes)} emails de test ({fichier})\n")

modele, vocab = charger()


def poids(r):
    e = SimpleNamespace(
        objet=r["objet"], extrait=r["extrait"], expediteur=r["expediteur"], texte_pj=r.get("texte_pj")
    )
    return classer_poids(e)[0]


def torch_(r):
    return predire(modele, vocab, r["objet"], r["extrait"], r["expediteur"], r.get("texte_pj"))[0]


resultats = {}
for nom, f in (("score a poids", poids), ("PyTorch", torch_)):
    t0 = time.perf_counter()
    preds = [f(r) for r in lignes]
    duree = (time.perf_counter() - t0) / len(lignes) * 1000
    ok = sum(p == r["etiquette"] for p, r in zip(preds, lignes))
    resultats[nom] = preds
    print(f"{nom:14s} precision : {ok}/{len(lignes)} = {ok / len(lignes):.1%}   ({duree:.2f} ms par email)")

print("\nPrecision par categorie (justes / total)")
print(f"{'categorie':12s} {'poids':>8s} {'pytorch':>8s}")
for c in CLASSES:
    idx = [i for i, r in enumerate(lignes) if r["etiquette"] == c]
    if not idx:
        continue
    a = sum(resultats["score a poids"][i] == c for i in idx)
    b = sum(resultats["PyTorch"][i] == c for i in idx)
    print(f"{c:12s} {a:>4d}/{len(idx):<3d} {b:>4d}/{len(idx):<3d}")

print("\nErreurs :")
for i, r in enumerate(lignes):
    p1, p2 = resultats["score a poids"][i], resultats["PyTorch"][i]
    if p1 != r["etiquette"] or p2 != r["etiquette"]:
        print(f"- {r['objet'][:45]!r:48s} vrai={r['etiquette']:11s} poids={p1:11s} pytorch={p2}")
