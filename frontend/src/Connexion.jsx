import { useState } from "react";
import { appeler } from "./api";

export default function Connexion({ onConnecte }) {
  const [inscription, setInscription] = useState(false);
  const [nom, setNom] = useState("");
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState("");
  const [attente, setAttente] = useState(false);

  async function envoyer(e) {
    e.preventDefault();
    setErreur("");
    setAttente(true);
    try {
      if (inscription) {
        await appeler("/auth/register", {
          methode: "POST",
          corps: { nom, email, mot_de_passe: motDePasse },
        });
      }
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
        <h1>Automatisation des emails</h1>
        <p className="aide">
          {inscription ? "Creer un compte" : "Connectez-vous a votre compte"}
        </p>

        {inscription && (
          <label>
            Nom
            <input value={nom} onChange={(e) => setNom(e.target.value)} required />
          </label>
        )}
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Mot de passe
          <input
            type="password"
            value={motDePasse}
            onChange={(e) => setMotDePasse(e.target.value)}
            required
          />
        </label>

        {erreur && <p className="erreur">{erreur}</p>}

        <button type="submit" disabled={attente}>
          {attente ? "Patientez..." : inscription ? "S'inscrire" : "Se connecter"}
        </button>
        <button
          type="button"
          className="lien"
          onClick={() => {
            setInscription(!inscription);
            setErreur("");
          }}
        >
          {inscription ? "J'ai deja un compte" : "Creer un compte"}
        </button>
      </form>
    </main>
  );
}
