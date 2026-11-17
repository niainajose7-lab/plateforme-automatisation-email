// Adresse du backend FastAPI
export const API = "http://127.0.0.1:8000";

const CLE = "jeton";

export function lireJeton() {
  try {
    return localStorage.getItem(CLE) || "";
  } catch {
    return "";
  }
}

export function enregistrerJeton(jeton) {
  try {
    if (jeton) localStorage.setItem(CLE, jeton);
    else localStorage.removeItem(CLE);
  } catch {
    /* stockage indisponible : on continue sans */
  }
}

// Appel generique : renvoie le JSON, ou lance une Error avec le message du serveur
export async function appeler(chemin, { methode = "GET", corps, jeton } = {}) {
  const entetes = {};
  if (corps) entetes["Content-Type"] = "application/json";
  if (jeton) entetes["Authorization"] = "Bearer " + jeton;

  let reponse;
  try {
    reponse = await fetch(API + chemin, {
      method: methode,
      headers: entetes,
      body: corps ? JSON.stringify(corps) : undefined,
    });
  } catch {
    throw new Error("Impossible de joindre le serveur. Uvicorn est-il lance ?");
  }

  let donnees = null;
  try {
    donnees = await reponse.json();
  } catch {
    /* reponse sans JSON */
  }

  if (!reponse.ok) {
    let message = "Erreur " + reponse.status;
    if (donnees && typeof donnees.detail === "string") message = donnees.detail;
    else if (donnees && Array.isArray(donnees.detail))
      message = donnees.detail.map((d) => d.msg).join(" ; ");
    const erreur = new Error(message);
    erreur.statut = reponse.status;
    throw erreur;
  }
  return donnees;
}
