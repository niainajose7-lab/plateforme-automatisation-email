import os
import sys

from ocr import lire_image
from extraction import extraire


def creer_exemple(chemin):
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (900, 500), "white")
    dessin = ImageDraw.Draw(image)
    try:
        police = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
    except OSError:
        try:
            police = ImageFont.truetype("DejaVuSans.ttf", 36)
        except OSError:
            police = ImageFont.load_default()

    lignes = [
        "FACTURE N 2026-045",
        "Societe Exemple SARL",
        "Date : 28/10/2026",
        "Montant total : 120,50 EUR",
        "Echeance : 15/11/2026",
    ]
    y = 40
    for ligne in lignes:
        dessin.text((50, y), ligne, fill="black", font=police)
        y += 80
    image = image.rotate(2, expand=True, fillcolor="white")
    image.save(chemin)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        chemin = sys.argv[1]
    else:
        chemin = "facture_test.png"
        creer_exemple(chemin)
        print("Image d'exemple creee :", os.path.abspath(chemin))

    print("Lecture en cours (le premier lancement est long)...")
    texte = lire_image(chemin)
    print("----- TEXTE LU -----")
    print(texte)
    print("--------------------")
    print("----- DONNEES EXTRAITES -----")
    for cle, valeur in extraire(texte).items():
        print(cle, ":", valeur)