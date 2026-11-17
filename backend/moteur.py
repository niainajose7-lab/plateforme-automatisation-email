CHAMPS = ("objet", "expediteur", "extrait", "categorie")
OPERATEURS = ("contient", "egal", "commence_par")


def evaluer(condition: dict, email) -> bool:
    champ = condition.get("champ")
    operateur = condition.get("operateur")
    valeur = str(condition.get("valeur", "")).lower()

    if champ not in CHAMPS or operateur not in OPERATEURS:
        return False

    texte = (getattr(email, champ, "") or "").lower()

    if operateur == "contient":
        return valeur in texte
    if operateur == "egal":
        return texte == valeur
    if operateur == "commence_par":
        return texte.startswith(valeur)
    return False
