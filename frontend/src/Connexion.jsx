import { useState } from "react";
import { appeler } from "./api";

export default function Connexion({ onConnecte }) {
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState("");
  const [attente, setAttente] = useState(false);

  async function envoyer(e) {
    e.preventDefault();
    setErreur("");
    setAttente(true);
    try {
      const jeton = await appeler("/auth/login", {
        methode: "POST",
        corps: { email, mot_de_passe: motDePasse },
      });
      onConnecte(jeton.access_token);
    } catch (err) {
      setErreur(err.message);
    } finally {
      setAttente(false);
    }
  }

  return (
    <main className="centre">
      <form className="carte" onSubmit={envoyer}>
        <div className="logo" style={{ padding: 0 }}>
          <div className="pastille" style={{ background: "#2457D6", color: "#fff", width: 40, height: 40, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800 }}>A</div>
          <div>
            <b style={{ fontSize: 20, color: "#0F172A" }}>AutoMail</b>
            <small style={{ display: "block", color: "#475467" }}>Automatisation des emails</small>
          </div>
        </div>
        <p className="aide">Connectez-vous à votre espace (administrateur ou client).</p>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Mot de passe
          <input type="password" value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} required />
        </label>
        {erreur && <p className="erreur">{erreur}</p>}
        <button type="submit" disabled={attente}>{attente ? "Patientez..." : "Se connecter"}</button>
        <p className="info" style={{ textAlign: "center", margin: 0 }}>Pas de compte ? Contactez votre administrateur.</p>
      </form>
    </main>
  );
}
