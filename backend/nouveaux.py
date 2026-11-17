import csv

def lire(chemin):
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))

anciens = {r["id"] for r in lire("dataset_35.csv")}
nouveaux = [r for r in lire("dataset.csv") if r["id"] not in anciens]
print(len(nouveaux), "nouveaux emails\n")
for i, r in enumerate(nouveaux, 1):
    exp = r["expediteur"].split("<")[-1].strip("> ")
    print(f"{i}. objet={r['objet'][:60]!r} | de={exp[:35]} | actuel={r['etiquette']}")