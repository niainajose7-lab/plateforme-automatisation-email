import { useEffect, useState } from "react";
import { appeler } from "./api";

const TAILLE_MAX = 5 * 1024 * 1024; // 5 Mo

// Lit un fichier et renvoie son contenu en base64
function lireFichier(fichier) {
  return new Promise((resolve, reject) => {
    const lecteur = new FileReader();
    lecteur.onload = () => resolve(String(lecteur.result).split(",")[1] || "");
    lecteur.onerror = () => reject(new Error("Lecture du fichier impossible"));
    lecteur.readAsDataURL(fichier);
  });
}

export default function Envoyer({ jeton, onDeconnexion }) {
  const [boites, setBoites] = useState([]);
  const [boiteId, setBoiteId] = useState("");
  const [destinataire, setDestinataire] = useState("");
  const [objet, setObjet] = useState("");
  const [corps, setCorps] = useState("");
  const [fichier, setFichier] = useState(null);
  const [erreur, setErreur] = useState("");
  const [info, setInfo] = useState("");
  const [attente, setAttente] = useState(false);

  useEffect(() => {
    appeler("/emails/", { jeton })
      .then((liste) => {
        setBoites(liste);
        if (liste.length > 0) setBoiteId((actuel) => actuel || liste[0].id);
      })
      .catch((err) => {
        if (err.statut === 401) onDeconnexion();
        else setErreur(err.message);
      });
  }, [jeton, onDeconnexion]);

  function choisirFichier(e) {
    const f = e.target.files[0] || null;
    setErreur("");
    if (f && f.size > TAILLE_MAX) {
      setErreur("Fichier trop volumineux (5 Mo maximum).");
      e.target.value = "";
      setFichier(null);
      return;
    }
    setFichier(f);
  }

  async function envoyer(e) {
    e.preventDefault();
    setErreur("");
    setInfo("");
    setAttente(true);
    try {
      const corpsRequete = { destinataire, objet, corps };
      if (fichier) {
        corpsRequete.piece_jointe = {
          nom: fichier.name,
          type: fichier.type || "application/octet-stream",
          donnees_base64: await lireFichier(fichier),
        };
      }
      await appeler("/emails/" + boiteId + "/envoyer", {
        jeton,
        methode: "POST",
        corps: corpsRequete,
      });
      setInfo(
        "Email envoye a " + destinataire + ". S'il est destine a votre propre boite, il apparaitra dans le suivi dans environ une minute."
      );
      setDestinataire("");
      setObjet("");
      setCorps("");
      setFichier(null);
      e.target.reset();
    } catch (err) {
      if (err.statut === 401) onDeconnexion();
      else setErreur(err.message);
    } finally {
      setAttente(false);
    }
  }

  const boite = boites.find((b) => b.id === boiteId);

  return (
    <section className="bloc">
      <h2>Nouveau message</h2>
      {boites.length === 0 ? (
        <p className="aide">Connectez d'abord une boite Gmail (onglet Suivi).</p>
      ) : (
        <form className="formulaire" onSubmit={envoyer}>
          {boites.length > 1 ? (
            <label>
              Envoyer depuis
              <select value={boiteId} onChange={(e) => setBoiteId(e.target.value)}>
                {boites.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.adresse}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <p className="aide">Envoye depuis : {boite && boite.adresse}</p>
          )}
          <label>
            A
            <input
              type="email"
              value={destinataire}
              onChange={(e) => setDestinataire(e.target.value)}
              placeholder="adresse@exemple.com"
              required
            />
          </label>
          <label>
            Objet
            <input value={objet} onChange={(e) => setObjet(e.target.value)} required />
          </label>
          <label>
            Message
            <textarea
              rows={6}
              value={corps}
              onChange={(e) => setCorps(e.target.value)}
              required
            />
          </label>
          <label>
            Piece jointe (facultatif, 5 Mo maximum)
            <input type="file" onChange={choisirFichier} />
          </label>

          {erreur && <p className="erreur">{erreur}</p>}
          {info && <p className="succes">{info}</p>}
          <div>
            <button type="submit" disabled={attente || !boiteId}>
              {attente ? "Envoi..." : "Envoyer"}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
