"""Genere train.csv : exemples d'entrainement synthetiques (francais), 10 classes."""
import csv
import random

random.seed(7)

MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
        "aout", "septembre", "octobre", "novembre", "decembre"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
PRODUITS = ["ordinateurs portables", "telephones", "imprimantes", "chaises de bureau",
            "ecrans", "serveurs", "tablettes", "climatiseurs", "photocopieuses"]
POSTES = ["comptable", "developpeur web", "secretaire", "assistant commercial",
          "technicien reseau", "responsable logistique", "infirmier", "enseignant"]
PRENOMS = ["jean", "hery", "lalaina", "sophie", "marc", "fanja", "paul", "nadia", "tiana", "mamy"]
NOMS = ["rakoto", "rasoa", "andria", "ravelo", "martin", "dubois", "randria", "bernard"]
ENTREPRISES = ["sotrapa", "madatech", "agrimad", "telmada", "ocean-services", "habitat-plus",
               "univ-tana", "banque-sud", "alpha-conseil", "eco-pharma"]
FINS = ["", "", "", " Cordialement.", " Merci d'avance.", " Bonne journee.",
        " Veuillez agreer mes salutations distinguees.", " Dans l'attente de votre retour."]

D = {
    "facture": (
        ["Facture {n}", "Facture n {n} - {ent}", "Votre facture de {mois}", "Facture impayee {n}",
         "Envoi de la facture {n}", "Releve de facture {n}"],
        ["Veuillez trouver ci-joint la facture {n} d'un montant de {m}.",
         "Merci de regler la facture {n} de {m} avant le {d}.",
         "Voici la facture de votre achat, total a payer {m}, echeance {d}.",
         "Facture {n} en piece jointe, montant TTC {m}, paiement avant le {d}.",
         "Rappel : la facture {n} de {m} reste impayee."]),
    "reclamation": (
        ["Reclamation commande {n}", "Je ne suis pas satisfait", "Plainte concernant votre service",
         "Produit defectueux", "Probleme avec ma livraison", "Remboursement demande"],
        ["Je souhaite faire une reclamation : le produit recu est defectueux, je demande un remboursement.",
         "Ma commande {n} est arrivee endommagee, je suis tres mecontent et j'exige une solution.",
         "Je n'ai jamais recu mon colis malgre le paiement, merci de regler ce probleme rapidement.",
         "Le service est inacceptable, je depose une plainte concernant la commande {n}.",
         "Livraison en retard de deux semaines, je reclame un geste commercial."]),
    "devis": (
        ["Demande de devis", "Devis pour {prod}", "Pouvez-vous m'envoyer un devis ?",
         "Demande de prix {prod}", "Besoin d'un devis"],
        ["Bonjour, pouvez-vous m'etablir un devis pour {q} {prod} ?",
         "Nous souhaitons recevoir une proposition de prix pour la creation d'un site web.",
         "Quel serait le tarif pour {q} {prod} livres a Antananarivo ?",
         "Merci de nous envoyer votre meilleur prix et vos delais pour {q} {prod}.",
         "Je voudrais un devis detaille pour l'installation de {q} {prod}."]),
    "commande": (
        ["Commande {n}", "Nouvelle commande {prod}", "Bon de commande {n}", "Je passe commande",
         "Confirmation de commande {n}"],
        ["Je souhaite passer commande de {q} {prod}, livraison avant le {d}.",
         "Veuillez trouver le bon de commande {n} pour {q} {prod}.",
         "Nous confirmons notre commande {n} de {q} {prod}, merci de l'expedier rapidement.",
         "Je commande {q} {prod} comme convenu, paiement a la livraison.",
         "Ci-joint notre bon de commande {n}, montant {m}."]),
    "bourse": (
        ["Demande de bourse", "Dossier de bourse d'etudes", "Bourse {ann}",
         "Bourse universitaire : documents", "Renseignements sur la bourse"],
        ["Je depose mon dossier de demande de bourse d'etudes pour l'annee universitaire {ann}.",
         "Voici mon dossier de bourse : releve de notes, certificat de scolarite et lettre de motivation.",
         "Je souhaite savoir quels documents fournir pour obtenir une bourse d'etudes.",
         "Etudiant en licence, je sollicite une bourse pour financer mes etudes a l'universite.",
         "Merci de me confirmer la date limite de depot du dossier de bourse."]),
    "reunion": (
        ["Rendez-vous {jour}", "Reunion {jour} a {h}h", "Demande de rendez-vous",
         "Invitation a une reunion", "Changement d'horaire de la reunion"],
        ["Pouvons-nous nous rencontrer {jour} a {h}h pour discuter du projet ?",
         "Je vous invite a la reunion d'equipe {jour} a {h}h en salle {n}.",
         "Serait-il possible de reporter notre rendez-vous de {jour} a {h}h ?",
         "Je propose un rendez-vous le {d} a {h}h, dites-moi si cela vous convient.",
         "Rappel : reunion {jour} a {h}h, merci de confirmer votre presence."]),
    "support": (
        ["Probleme de connexion", "Mon application ne fonctionne plus", "Erreur lors de l'installation",
         "Besoin d'aide technique", "Panne sur {prod}"],
        ["Je n'arrive pas a me connecter a mon compte, le site affiche l'erreur {n}.",
         "L'application plante au demarrage depuis la derniere mise a jour, pouvez-vous m'aider ?",
         "Mes {prod} ne s'allument plus, j'ai besoin d'une assistance technique.",
         "Impossible d'installer le logiciel, message d'erreur {n}, merci de m'aider.",
         "Je ne recois pas le code de verification et l'acces a mon compte est bloque."]),
    "candidature": (
        ["Candidature au poste de {poste}", "Candidature spontanee", "Postuler : {poste}",
         "Offre d'emploi {poste}", "Envoi de mon CV"],
        ["Je vous adresse ma candidature au poste de {poste}, mon CV et ma lettre de motivation sont joints.",
         "Interesse par l'offre d'emploi de {poste}, je vous envoie mon CV.",
         "Je me permets de postuler spontanement, vous trouverez mon CV ci-joint.",
         "Diplome en gestion avec {a} ans d'experience, je candidate au poste de {poste}.",
         "Veuillez trouver ma lettre de motivation et mon curriculum vitae pour le poste de {poste}."]),
    "information": (
        ["Demande d'informations", "Renseignements", "Question sur vos services",
         "Horaires d'ouverture", "Information sur vos activites"],
        ["Bonjour, pourriez-vous m'indiquer vos horaires d'ouverture et votre adresse ?",
         "Je voudrais plus d'informations sur vos services et vos conditions.",
         "Pouvez-vous m'expliquer comment fonctionne votre service et comment vous contacter ?",
         "Merci de m'envoyer une brochure presentant vos activites.",
         "J'aimerais savoir si vous proposez des formations et a quelles conditions."]),
    "autre": (
        ["Bonne annee", "Merci", "Photos de vacances", "Salut", "Anniversaire de {prenom}",
         "Invitation mariage", "Nouvelles de la famille"],
        ["Salut, comment vas-tu ? Je pensais a toi, on se voit ce week-end ?",
         "Merci beaucoup pour hier, c'etait tres sympa.",
         "Voici les photos de nos vacances, j'espere qu'elles te plairont.",
         "Je te souhaite une tres bonne annee, pleine de joie et de sante.",
         "Bonne chance pour tes examens, je pense bien a toi.",
         "Nous nous marions en {mois}, nous serions ravis de te compter parmi nous."]),
}
PAR_CLASSE = {c: 130 for c in D}
PAR_CLASSE["autre"] = 200


def remplir(modele):
    return modele.format(
        n=random.randint(100, 9999), m="%d Ar" % (random.randint(2, 950) * 1000),
        d="%d %s" % (random.randint(1, 28), random.choice(MOIS)), mois=random.choice(MOIS),
        prod=random.choice(PRODUITS), q=random.randint(2, 60), jour=random.choice(JOURS),
        h=random.randint(8, 17), ann="%d-%d" % (2025, 2026), poste=random.choice(POSTES),
        a=random.randint(1, 9), prenom=random.choice(PRENOMS), ent=random.choice(ENTREPRISES))


def expediteur():
    p, n, e = random.choice(PRENOMS), random.choice(NOMS), random.choice(ENTREPRISES)
    return random.choice([
        "%s.%s@gmail.com" % (p, n), "contact@%s.mg" % e, "%s@%s.com" % (p, e),
        "%s%d@yahoo.fr" % (n, random.randint(1, 99)), "info@%s.org" % e])


lignes = []
for classe, nb in PAR_CLASSE.items():
    sujets, corps = D[classe]
    for _ in range(nb):
        lignes.append({
            "expediteur": expediteur(),
            "objet": remplir(random.choice(sujets)),
            "extrait": remplir(random.choice(corps)) + random.choice(FINS),
            "etiquette": classe,
        })
random.shuffle(lignes)

with open("train.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["expediteur", "objet", "extrait", "etiquette"], delimiter=";")
    w.writeheader()
    w.writerows(lignes)
print("train.csv :", len(lignes), "exemples")
