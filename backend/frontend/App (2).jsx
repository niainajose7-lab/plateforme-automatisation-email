import { useState } from "react";
import { lireJeton, enregistrerJeton } from "./api";
import Connexion from "./Connexion";
import Tableau from "./Tableau";
import Regles from "./Regles";
import Envoyer from "./Envoyer";

export default function App() {
  const [jeton, setJeton] = useState(lireJeton());
  const [onglet, setOnglet] = useState("suivi");

  function connecter(nouveau) {
    enregistrerJeton(nouveau);
    setJeton(nouveau);
  }

  function deconnecter() {
    enregistrerJeton("");
    setJeton("");
  }

  if (!jeton) return <Connexion onConnecte={connecter} />;

  return (
    <div className="page">
      <header className="barre">
        <h1>Automatisation des emails</h1>
        <button className="secondaire" onClick={deconnecter}>
          Deconnexion
        </button>
      </header>

      <nav className="onglets">
        <button
          className={onglet === "suivi" ? "actif" : ""}
          onClick={() => setOnglet("suivi")}
        >
          Suivi des emails
        </button>
        <button
          className={onglet === "regles" ? "actif" : ""}
          onClick={() => setOnglet("regles")}
        >
          Regles
        </button>
        <button
          className={onglet === "envoyer" ? "actif" : ""}
          onClick={() => setOnglet("envoyer")}
        >
          Envoyer un email
        </button>
      </nav>

      {onglet === "suivi" && <Tableau jeton={jeton} onDeconnexion={deconnecter} />}
      {onglet === "regles" && <Regles jeton={jeton} onDeconnexion={deconnecter} />}
      {onglet === "envoyer" && <Envoyer jeton={jeton} onDeconnexion={deconnecter} />}
    </div>
  );
}
