import os
import unicodedata

from dotenv import load_dotenv

load_dotenv()

# Score a partir duquel on est sur a 100 % de la categorie
SATURATION = 6.0

# Poids des indices pour chaque categorie
CATEGORIES = {
    "facture": {
        "mots": {
            "facture": 3, "invoice": 3, "montant": 2, "paiement": 2,
            "payer": 2, "reglement": 2, "echeance": 2, "euro": 1, "tva": 2,
        },
        "expediteurs": {"compta": 3, "facturation": 3, "billing": 3},
    },
    "reclamation": {
        "mots": {
            "reclamation": 3, "plainte": 3, "insatisfait": 3, "probleme": 1,
            "remboursement": 2, "defectueux": 2, "retard": 2, "erreur": 1,
            "inacceptable": 2, "livraison": 1,
        },
        "expediteurs": {"sav": 2},
    },
    "devis": {
        "mots": {
            "devis": 3, "tarif": 2, "prix": 2, "combien coute": 3,
            "demande de prix": 3, "proposition": 1, "quantite": 1, "estimation": 2,
        },
        "expediteurs": {"commercial": 1},
    },
    "commande": {
        "mots": {
            "commande": 3, "bon de commande": 3, "commander": 2,
            "passer commande": 3, "livraison": 1, "article": 1,
        },
        "expediteurs": {"vente": 1},
    },
    "bourse": {
        "mots": {
            "bourse": 3, "demande de bourse": 3, "dossier": 2, "inscription": 2,
            "pieces justificatives": 3, "scolarite": 2, "universite": 1, "etudiant": 1,
        },
        "expediteurs": {"scolarite": 2},
    },
    "reunion": {
        "mots": {
            "reunion": 3, "rendez-vous": 3, "rdv": 2, "disponibilite": 1,
            "disponible": 1, "invitation": 2, "convocation": 2, "agenda": 1,
        },
        "expediteurs": {"secretariat": 1},
    },
    "support": {
        "mots": {
            "ne fonctionne pas": 3, "bug": 3, "panne": 3, "mot de passe oublie": 3,
            "connexion": 2, "impossible de": 2, "assistance": 2, "installation": 1,
        },
        "expediteurs": {"support": 2, "helpdesk": 3},
    },
    "candidature": {
        "mots": {
            "candidature": 3, "cv": 2, "lettre de motivation": 3, "stage": 2,
            "emploi": 2, "recrutement": 2, "postuler": 2, "poste": 1,
        },
        "expediteurs": {"recrutement": 2, "rh": 1},
    },
    "information": {
        "mots": {
            "information": 2, "renseignement": 2, "question": 1, "horaires": 2,
            "souhaite savoir": 2, "pouvez-vous": 1, "je voudrais": 1,
        },
        "expediteurs": {"contact": 2, "info": 2},
    },
}


def normaliser(texte):
    texte = unicodedata.normalize("NFD", (texte or "").lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def scorer(email):
    objet = normaliser(getattr(email, "objet", ""))
    extrait = normaliser(getattr(email, "extrait", ""))
    expediteur = normaliser(getattr(email, "expediteur", ""))
    pieces = normaliser(getattr(email, "texte_pj", ""))

    scores = {}
    for nom, indices in CATEGORIES.items():
        total = 0.0
        for mot, poids in indices["mots"].items():
            if mot in objet:
                total += poids * 2  # un mot dans l'objet compte double
            if mot in extrait:
                total += poids
            if mot in pieces:
                total += poids  # texte lu dans les pieces jointes
        for morceau, poids in indices["expediteurs"].items():
            if morceau in expediteur:
                total += poids
        scores[nom] = total
    return scores


def classer_poids(email):
    scores = scorer(email)
    classement = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    meilleur_nom, meilleur = classement[0]
    second = classement[1][1]

    if meilleur <= 0:
        return "autre", 0.0

    confiance = min(1.0, meilleur / SATURATION)
    if second > 0:
        # Si une autre categorie est proche, on doute davantage
        confiance *= (meilleur - second * 0.5) / meilleur
    return meilleur_nom, round(min(0.95, confiance), 2)


# --- Choix de la methode : CLASSIFIEUR=poids (defaut) ou CLASSIFIEUR=pytorch dans .env ---

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_modele = None
_pytorch_indisponible = False


def _charger_pytorch():
    global _modele, _pytorch_indisponible
    if _modele is None and not _pytorch_indisponible:
        try:
            from modele_pytorch import charger

            _modele = charger(
                os.path.join(_DOSSIER, "modele.pt"),
                os.path.join(_DOSSIER, "vocab.json"),
            )
            print("[classifieur] PyTorch charge")
        except Exception as err:
            _pytorch_indisponible = True
            print("[classifieur] PyTorch indisponible, repli sur le score a poids :", type(err).__name__, err)
    return _modele


def classer_pytorch(email):
    charge = _charger_pytorch()
    if charge is None:
        return classer_poids(email)
    from modele_pytorch import predire

    modele, vocab = charge
    categorie, confiance = predire(
        modele, vocab, email.objet, email.extrait, email.expediteur,
        getattr(email, "texte_pj", None),
    )
    return categorie, round(min(0.95, 0.5 + 0.45 * confiance), 2)


def classer(email):
    """Point d'entree utilise par la boucle automatique."""
    if os.getenv("CLASSIFIEUR", "poids").strip().lower() == "pytorch":
        try:
            return classer_pytorch(email)
        except Exception as err:
            print("[classifieur] erreur PyTorch, repli sur le score a poids :", type(err).__name__, err)
    return classer_poids(email)
