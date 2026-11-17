import { useEffect, useState } from "react";
import { API, lireJeton, enregistrerJeton } from "./api";
import Connexion from "./Connexion";
import Tableau from "./Tableau";
import Regles from "./Regles";
import Envoyer from "./Envoyer";
import Fonctionnement from "./Fonctionnement";

function useEtatServeur() {
  const [ok, setOk] = useState(null);
  useEffect(() => {
    let actif = true;
    function verifier() {
      fetch(API + "/")
        .then((r) => actif && setOk(r.ok))
        .catch(() => actif && setOk(false));
    }
    verifier();
    const minuteur = setInterval(verifier, 8000);
    return () => {
      actif = false;
      clearInterval(minuteur);
    };
  }, []);
  return ok;
}

export default function App() {
  const [jeton, setJeton] = useState(lireJeton());
  const [onglet, setOnglet] = useState("suivi");
  const serveur = useEtatServeur();

  function connecter(nouveau) {
    enregistrerJeton(nouveau);
    setJeton(nouveau);
  }

  function deconnecter() {
    enregistrerJeton("");
    setJeton("");
  }

  const bandeau =
    serveur === false ? (
      <div className="alerte-bloc">
        <strong>Le serveur est injoignable.</strong> Lance le backend : dans le dossier
        <code> backend</code>, active le venv puis tape <code>uvicorn main:app --reload</code>.
      </div>
    ) : null;

  if (!jeton)
    return (
      <>
        {bandeau}
        <Connexion onConnecte={connecter} />
      </>
    );

  const onglets = [
    ["suivi", "Suivi des emails"],
    ["regles", "Règles"],
    ["envoyer", "Envoyer un email"],
    ["aide", "Fonctionnement"],
  ];

  return (
    <div className="page">
      <header className="barre">
        <h1>Automatisation des emails</h1>
        <div className="actions">
          <span className={"badge " + (serveur ? "ok" : serveur === false ? "alerte" : "")}>
            {serveur ? "Serveur connecté" : serveur === false ? "Serveur injoignable" : "Vérification…"}
          </span>
          <button className="secondaire" onClick={deconnecter}>
            Déconnexion
          </button>
        </div>
      </header>

      {bandeau}

      <nav className="onglets">
        {onglets.map(([cle, libelle]) => (
          <button
            key={cle}
            className={onglet === cle ? "actif" : ""}
            onClick={() => setOnglet(cle)}
          >
            {libelle}
          </button>
        ))}
      </nav>

      {onglet === "suivi" && <Tableau jeton={jeton} onDeconnexion={deconnecter} />}
      {onglet === "regles" && <Regles jeton={jeton} onDeconnexion={deconnecter} />}
      {onglet === "envoyer" && <Envoyer jeton={jeton} onDeconnexion={deconnecter} />}
      {onglet === "aide" && <Fonctionnement />}
    </div>
  );
}
