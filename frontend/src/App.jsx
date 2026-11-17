import { useCallback, useEffect, useState } from "react";
import { API, lireJeton, enregistrerJeton, appeler } from "./api";
import Connexion from "./Connexion";
import Accueil from "./Accueil";
import SuiviEmails from "./SuiviEmails";
import Categories from "./Categories";
import Clients from "./Clients";
import Alertes from "./Alertes";

export default function App() {
  const [jeton, setJeton] = useState(lireJeton());
  const [page, setPage] = useState("accueil");
  const [serveur, setServeur] = useState(null);
  const [compteurs, setCompteurs] = useState({ a_valider: 0, alertes: 0 });
  const [refus, setRefus] = useState("");

  const deconnecter = useCallback(() => {
    enregistrerJeton("");
    setJeton("");
  }, []);

  function connecter(nouveau) {
    enregistrerJeton(nouveau);
    setJeton(nouveau);
    setRefus("");
  }

  useEffect(() => {
    let actif = true;
    function verifier() {
      fetch(API + "/").then((r) => actif && setServeur(r.ok)).catch(() => actif && setServeur(false));
      if (!jeton) return;
      appeler("/admin/tableau", { jeton })
        .then((d) => actif && setCompteurs({ a_valider: d.totaux.a_valider, alertes: d.alertes_ouvertes }))
        .catch((e) => {
          if (!actif) return;
          if (e.statut === 401) deconnecter();
          if (e.statut === 403) setRefus(e.message);
        });
    }
    verifier();
    const t = setInterval(verifier, 15000);
    return () => { actif = false; clearInterval(t); };
  }, [jeton, deconnecter]);

  if (!jeton)
    return (
      <>
        {serveur === false && <div className="alerte-bloc"><strong>Le serveur est injoignable.</strong> Lance uvicorn dans le dossier backend.</div>}
        <Connexion onConnecte={connecter} />
      </>
    );

  const items = [
    ["accueil", "Tableau de bord", 0, ""],
    ["suivi", "Suivi des emails", compteurs.a_valider, ""],
    ["categories", "Catégories et règles", 0, ""],
    ["clients", "Clients", 0, ""],
    ["alertes", "Alertes", compteurs.alertes, "rouge"],
  ];
  const p = { jeton, onDeconnexion: deconnecter, aller: setPage };

  return (
    <div className="app">
      <aside className="menu">
        <div className="logo">
          <div className="pastille">A</div>
          <div><b>AutoMail</b><small>Espace administrateur</small></div>
        </div>
        <nav>
          {items.map(([cle, nom, n, couleur]) => (
            <button key={cle} className={page === cle ? "actif" : ""} onClick={() => setPage(cle)}>
              {nom}
              {n > 0 && <span className={"pastille-n " + couleur}>{n}</span>}
            </button>
          ))}
        </nav>
        <div className="bas">
          <div className="profil">
            <b>Administrateur</b>
            {serveur ? "Serveur connecté" : serveur === false ? "Serveur injoignable" : "Vérification..."}
          </div>
          <button className="deco" onClick={deconnecter}>Déconnexion</button>
        </div>
      </aside>
      <main className="contenu">
        {refus && <div className="bandeau-alerte">{refus}</div>}
        {page === "accueil" && <Accueil {...p} />}
        {page === "suivi" && <SuiviEmails {...p} />}
        {page === "categories" && <Categories {...p} />}
        {page === "clients" && <Clients {...p} />}
        {page === "alertes" && <Alertes {...p} />}
      </main>
    </div>
  );
}
