import { useState } from "react";
import { lireJeton, enregistrerJeton } from "./api";
import Connexion from "./Connexion";
import Tableau from "./Tableau";

export default function App() {
  const [jeton, setJeton] = useState(lireJeton());

  function connecter(nouveau) {
    enregistrerJeton(nouveau);
    setJeton(nouveau);
  }

  function deconnecter() {
    enregistrerJeton("");
    setJeton("");
  }

  return jeton ? (
    <Tableau jeton={jeton} onDeconnexion={deconnecter} />
  ) : (
    <Connexion onConnecte={connecter} />
  );
}
