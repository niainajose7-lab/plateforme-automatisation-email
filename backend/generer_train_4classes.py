"""Genere train.csv : exemples d'entrainement synthetiques (francais), 4 categories."""
import csv
import random

random.seed(42)

MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
        "aout", "septembre", "octobre", "novembre", "decembre"]
PRODUITS = ["ordinateur portable", "telephone", "imprimante", "chaise de bureau",
            "abonnement", "machine a cafe", "casque audio", "ecran", "clavier",
            "pack de formation", "licence logiciel", "table", "robe", "sac"]
PRENOMS = ["Jean", "Hery", "Lalaina", "Sophie", "Marc", "Fanja", "Paul", "Nadia"]


def montant():
    v = random.choice([2500, 15000, 45900, 120000, 350000, 89, 450, 1200, 75, 19.99])
    u = random.choice(["Ar", "MGA", "EUR", "USD", "euros", "Ariary"])
    return f"{v} {u}"


def num():
    return random.choice(["2026-", "FAC-", "INV-", "N", ""]) + str(random.randint(10, 9999))


def date():
    return f"{random.randint(1, 28)} {random.choice(MOIS)} 2026"


def choisir(listes):
    return random.choice(listes)


# ---------- FACTURE ----------
def facture():
    sujets = [
        f"Facture {num()}", f"Votre facture de {random.choice(MOIS)}",
        f"Avis d'echeance {num()}", f"Facture impayee {num()}",
        f"Recu de paiement {num()}", f"Devis et facture {random.choice(PRODUITS)}",
        "Rappel : facture a regler", f"Relance paiement facture {num()}",
        f"Facture proforma {num()}", "Votre releve de compte et facture",
    ]
    corps = [
        f"Veuillez trouver ci-joint la facture {num()} d'un montant de {montant()}.",
        f"Montant total a payer : {montant()}. Date limite de reglement : {date()}.",
        f"Nous vous rappelons que la facture {num()} reste impayee. Merci de regulariser avant le {date()}.",
        f"Votre paiement de {montant()} a bien ete recu. Vous trouverez le recu en piece jointe.",
        f"Facture pour l'achat de {random.choice(PRODUITS)}. Total TTC : {montant()}. Echeance : {date()}.",
        f"Ci-joint votre facture mensuelle. Montant : {montant()}. Merci de proceder au reglement par virement.",
        f"Bonjour, voici le devis puis la facture pour {random.choice(PRODUITS)}, total {montant()} TVA incluse.",
    ]
    exp = ["comptabilite@", "facturation@", "billing@", "paiements@", "contact@"]
    return choisir(sujets), choisir(corps), choisir(exp) + choisir(["entreprise.mg", "societe.com", "services.fr", "boutique.mg"])


# ---------- RECLAMATION ----------
def reclamation():
    sujets = [
        "Reclamation", f"Probleme avec ma commande {num()}", "Je ne suis pas satisfait",
        "Colis non recu", "Article defectueux", "Plainte concernant votre service",
        "Demande de remboursement urgent", "Livraison en retard", "Service inacceptable",
        "Produit non conforme", "Insatisfait de mon achat", "Erreur dans ma commande",
    ]
    corps = [
        f"Je n'ai toujours pas recu mon {random.choice(PRODUITS)} commande il y a deux semaines. C'est inadmissible.",
        f"Le {random.choice(PRODUITS)} recu est casse. Je suis tres decu et je souhaite etre rembourse.",
        "Je suis extremement mecontent de la qualite de votre service. Personne ne repond a mes messages.",
        f"Bonjour, je me plains du retard de livraison de ma commande {num()}. Ce n'est pas la premiere fois.",
        "Votre produit ne fonctionne pas comme annonce. Je reclame un remboursement ou un echange immediat.",
        "Je vous ecris pour signaler un probleme grave : on m'a livre le mauvais article et le service client ne me rappelle pas.",
        f"Je conteste le montant preleve de {montant()}. C'est une erreur, je demande une correction et des excuses.",
    ]
    exp = [f"{random.choice(PRENOMS).lower()}@gmail.com", f"{random.choice(PRENOMS).lower()}@yahoo.fr", "client@hotmail.com"]
    return choisir(sujets), choisir(corps), choisir(exp)


# ---------- DEMANDE ----------
def demande():
    sujets = [
        "Demande d'information", "Question sur votre offre", "Rendez-vous la semaine prochaine",
        f"Renseignements sur {random.choice(PRODUITS)}", "Pourriez-vous m'aider ?",
        "Demande de documents", "Disponibilite pour une reunion", "Besoin d'un devis",
        "Une question rapide", "Candidature spontanee", "Demande de partenariat",
        "Information sur les delais",
    ]
    corps = [
        f"Bonjour, pourriez-vous m'indiquer le prix et la disponibilite du {random.choice(PRODUITS)} ?",
        "Bonjour, je souhaiterais fixer un rendez-vous pour discuter de votre offre. Quelles sont vos disponibilites ?",
        "Pouvez-vous m'envoyer une presentation de vos services ainsi que vos conditions ? Merci d'avance.",
        "Je voudrais savoir comment m'inscrire a votre programme et quels documents fournir.",
        f"Serait-il possible d'obtenir un devis pour {random.randint(2, 100)} {random.choice(PRODUITS)} ?",
        "Bonjour, j'aimerais avoir plus d'informations sur les horaires et les tarifs. Pouvez-vous me repondre ?",
        "Je vous contacte pour savoir si vous recrutez et comment envoyer mon CV.",
    ]
    exp = [f"{random.choice(PRENOMS).lower()}@gmail.com", f"{random.choice(PRENOMS).lower()}@outlook.com", "prospect@entreprise.com"]
    return choisir(sujets), choisir(corps), choisir(exp)


# ---------- AUTRE (notifications, newsletters, promos, perso) ----------
def autre():
    plats = ["LinkedIn", "YouTube", "Spotify", "Netflix", "Amazon", "Canva", "GitHub", "X", "TikTok", "Pinterest"]
    p = choisir(plats)
    modeles = [
        (f"{random.choice(PRENOMS)} a consulte votre profil", f"{p} Voir qui a regarde votre profil cette semaine. Se desabonner", f"notifications@{p.lower()}.com"),
        (f"Les nouveautes de {p} ce mois-ci", f"Decouvrez les dernieres fonctionnalites {p}. Cliquez ici pour en savoir plus. Se desinscrire", f"news@{p.lower()}.com"),
        (f"-{random.choice([20, 30, 50])}% sur tout le site", "Offre limitee ce week-end seulement. Profitez de nos promotions exceptionnelles. Se desinscrire", f"promo@{p.lower()}.com"),
        ("Votre code de verification", f"Votre code de securite est {random.randint(100000, 999999)}. Ne le partagez avec personne.", f"no-reply@{p.lower()}.com"),
        ("Nouvelle connexion detectee", "Une nouvelle connexion a votre compte a ete detectee sur un appareil. Si c'etait vous, ignorez ce message.", f"security@{p.lower()}.com"),
        (f"{random.choice(PRENOMS)} vous a envoye un message", "Voir le message. Repondre depuis l'application. Se desabonner des notifications.", f"messages@{p.lower()}.com"),
        (f"{random.choice(PRENOMS)} a aime votre publication", f"{p} Voir la publication. Gerer les notifications.", f"notification@{p.lower()}.com"),
        ("Bienvenue sur la plateforme", "Votre compte a ete cree avec succes. Commencez a explorer les fonctionnalites.", f"hello@{p.lower()}.com"),
        ("Salut, ca va ?", "Coucou, on se voit samedi pour le match ? Dis-moi quand tu es dispo. A bientot", f"{random.choice(PRENOMS).lower()}@gmail.com"),
        ("Votre mise a jour est disponible", "Une nouvelle version est disponible. Mettez a jour pour profiter des ameliorations.", f"update@{p.lower()}.com"),
        ("Invitation a l'evenement", f"Vous etes invite a la soiree du {date()}. Confirmez votre presence.", f"events@{p.lower()}.com"),
        ("Decouvrez de nouvelles idees", f"Creez, essayez et partagez avec {p}. Explorez les nouveaux outils et laissez libre cours a votre creativite. Se desinscrire", f"hello@{p.lower()}.com"),
        (f"{random.randint(3, 8)} nouveaux modeles a essayer", f"Voyez vos contenus autrement avec {p}. Choisissez un style et explorez les possibilites. Essayer maintenant", f"news@{p.lower()}.com"),
        ("Posez toutes vos questions a l'assistant", f"Nouveau sur {p} : discutez, apprenez et trouvez des reponses. Commencez des maintenant", f"team@{p.lower()}.com"),
        ("Vous avez ete accepte dans le groupe", f"Votre adhesion au groupe a ete approuvee. Vous pouvez publier et commenter. Merci, l'equipe {p}", f"groups@{p.lower()}.com"),
        ("Confirmez votre adresse email", "Cliquez sur le lien pour verifier votre adresse et terminer la configuration de votre compte.", f"verify@{p.lower()}.com"),
        ("Candidature recue", "Nous avons bien recu votre candidature. Nous reviendrons vers vous apres la cloture des candidatures.", f"recrutement@{p.lower()}.com"),
        (random.choice(["Test", "Essai", "azerty", "hello", "Document", "Photo", "Fichier"]), random.choice(["", "Voir ci-joint", "Ci-joint", "ok", "test test"]), f"{random.choice(PRENOMS).lower()}@gmail.com"),
        ("Resume hebdomadaire", "Voici votre resume de la semaine : activites, nouveautes et recommandations pour vous.", f"digest@{p.lower()}.com"),
    ]
    return choisir(modeles)


GEN = {"facture": facture, "reclamation": reclamation, "demande": demande, "autre": autre}
PAR_CLASSE = {"facture": 90, "reclamation": 90, "demande": 90, "autre": 180}

lignes = []
for etiquette, f in GEN.items():
    vus = set()
    while len(vus) < PAR_CLASSE[etiquette]:
        s, c, e = f()
        vus.add((s, c, e))
    for s, c, e in vus:
        lignes.append([e, s, c, etiquette])

random.shuffle(lignes)
with open("train.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh, delimiter=";")
    w.writerow(["expediteur", "objet", "extrait", "etiquette"])
    w.writerows(lignes)
print("train.csv :", len(lignes), "exemples")
