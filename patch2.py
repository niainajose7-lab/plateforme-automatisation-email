def maj(f, a, b):
    t = open(f, encoding="utf-8-sig").read()
    if b in t:
        return print("deja fait :", f)
    assert t.count(a) == 1, "introuvable : " + a
    open(f, "w", encoding="utf-8").write(t.replace(a, b))
    print("OK :", f)

I = "backend/intelligence.py"
maj(I, "return categorie, round(confiance, 2)", "return categorie, round(min(0.95, 0.5 + 0.45 * confiance), 2)")
maj(I, "return meilleur_nom, round(confiance, 2)", "return meilleur_nom, round(min(0.95, confiance), 2)")
maj("backend/automatisation.py", '("spam", 1.0)', '("spam", 0.9)')
