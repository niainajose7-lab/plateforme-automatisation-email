import csv
import sys

VALIDES = ("facture", "reclamation", "demande", "autre")
labels = [x.strip() for x in sys.argv[1].split(",")]

def lire(chemin):
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        lecteur = csv.DictReader(f, delimiter=";")
        return lecteur.fieldnames, list(lecteur)

_, anciens = lire("dataset_35.csv")
ids_anciens = {r["id"] for r in anciens}
champs, lignes = lire("dataset.csv")
nouveaux = [r for r in lignes if r["id"] not in ids_anciens]

if len(labels) != len(nouveaux):
    sys.exit(f"Erreur : {len(labels)} etiquettes donnees, {len(nouveaux)} nouveaux emails.")
for l in labels:
    if l not in VALIDES:
        sys.exit(f"Etiquette invalide : {l!r} (valeurs : {', '.join(VALIDES)})")

for r, l in zip(nouveaux, labels):
    r["etiquette"] = l

with open("dataset.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
    w.writeheader()
    w.writerows(lignes)
print(len(nouveaux), "etiquettes mises a jour dans dataset.csv")