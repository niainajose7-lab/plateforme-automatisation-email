import json
import re
import unicodedata

import torch
import torch.nn as nn

CLASSES = ["facture", "reclamation", "demande", "autre"]
SEUIL_DOUTE = 0.6


def normaliser(texte):
    texte = unicodedata.normalize("NFD", (texte or "").lower())
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return texte


def jetons(texte):
    mots = re.findall(r"[a-z]+", normaliser(texte))
    return [m for m in mots if len(m) > 2]


def texte_email(objet, extrait, expediteur, texte_pj=None):
    # l'objet est repete : il pese plus, comme dans le score a poids
    domaine = (expediteur or "").split("@")[-1]
    return f"{objet} {objet} {extrait} {expediteur} {domaine} {texte_pj or ''}"


class Classifieur(nn.Module):
    def __init__(self, taille_vocab, nb_classes=len(CLASSES)):
        super().__init__()
        self.reseau = nn.Sequential(
            nn.Linear(taille_vocab, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, nb_classes),
        )

    def forward(self, x):
        return self.reseau(x)


def vecteur(texte, vocab):
    v = torch.zeros(len(vocab))
    for m in set(jetons(texte)):
        i = vocab.get(m)
        if i is not None:
            v[i] = 1.0
    return v


def charger(chemin_modele="modele.pt", chemin_vocab="vocab.json"):
    with open(chemin_vocab, encoding="utf-8") as f:
        vocab = json.load(f)
    modele = Classifieur(len(vocab))
    modele.load_state_dict(torch.load(chemin_modele, map_location="cpu"))
    modele.eval()
    return modele, vocab


def predire(modele, vocab, objet, extrait, expediteur, texte_pj=None):
    """Retourne (categorie, confiance entre 0 et 1)."""
    x = vecteur(texte_email(objet, extrait, expediteur, texte_pj), vocab)
    with torch.no_grad():
        p = torch.softmax(modele(x.unsqueeze(0)), dim=1)[0]
    i = int(p.argmax())
    conf = float(p[i])
    # Doute : mieux vaut "autre" (aucune action) qu'une mauvaise categorie
    if conf < SEUIL_DOUTE and CLASSES[i] != "autre":
        return "autre", conf
    return CLASSES[i], conf
