import cv2
import numpy as np

MAX_PAGES = 3  # on ne lit que les premieres pages d'un PDF

_lecteur = None


def lecteur():
    # Le modele est charge une seule fois (le chargement est lent)
    global _lecteur
    if _lecteur is None:
        import easyocr

        _lecteur = easyocr.Reader(["fr", "en"], gpu=False)
    return _lecteur


def pretraiter(image):
    """Nettoyage OpenCV : niveaux de gris, agrandissement, bruit."""
    if len(image.shape) == 3:
        gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gris = image

    hauteur, largeur = gris.shape
    if max(hauteur, largeur) < 1000:
        gris = cv2.resize(
            gris, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
        )

    gris = cv2.fastNlMeansDenoising(gris, None, 10, 7, 21)
    return gris


def _lire_matrice(image):
    traitee = pretraiter(image)
    lignes = lecteur().readtext(traitee, detail=0, paragraph=False)
    return "\n".join(lignes)


def lire_image(chemin):
    image = cv2.imread(chemin)
    if image is None:
        raise ValueError("Image illisible : " + chemin)
    return _lire_matrice(image)


def lire_octets(donnees, type_mime="", nom=""):
    """Lit le texte d'une image ou d'un PDF recu sous forme d'octets."""
    nom = (nom or "").lower()

    if type_mime == "application/pdf" or nom.endswith(".pdf"):
        import pymupdf

        textes = []
        with pymupdf.open(stream=donnees, filetype="pdf") as document:
            for numero, page in enumerate(document):
                if numero >= MAX_PAGES:
                    break
                # PDF numerique : le texte est deja la, pas besoin d'OCR
                natif = page.get_text().strip()
                if len(natif) > 20:
                    textes.append(natif)
                    continue
                pixels = page.get_pixmap(dpi=200)
                tampon = np.frombuffer(pixels.tobytes("png"), np.uint8)
                image = cv2.imdecode(tampon, cv2.IMREAD_COLOR)
                if image is not None:
                    textes.append(_lire_matrice(image))
        return "\n".join(textes)

    tampon = np.frombuffer(donnees, np.uint8)
    image = cv2.imdecode(tampon, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Image illisible")
    return _lire_matrice(image)
