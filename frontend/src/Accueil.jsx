import { useCallback, useEffect, useState } from "react";
import { appeler } from "./api";
import { libelleDecision, classeDecision, formatDate } from "./libelles";

export default function Accueil({ jeton, onDeconnexion, aller }) {
  const [d, setD] = useState(null);
  const [erreur, setErreur] = useState("");
  const [msg, setMsg] = useState("");
  const [attente, setAttente] = useState(false);

  const charger = useCallback(async () => {
    try {
      setD(await appeler("/admin/tableau", { jeton }));
      setErreur("");
    } catch (e) {
      if (e.statut === 401) onDeconnexion();
      else setErreur(e.message);
    }
  }, [jeton, onDeconnexion]);

  useEffect(() => {
    charger();
    const t = setInterval(charger, 15000);
    return () => clearInterval(t);
  }, [charger]);

  async function traiter() {
    setAttente(true);
    setMsg("");
    try {
      const boites = await appeler("/emails/", { jeton });
      if (!boites.length) throw new Error("Aucune boîte connectée");
      const r = await appeler("/emails/" + boites[0].id + "/traiter", { methode: "POST", jeton });
      setMsg(r.nouveaux + " nouveau(x) email(s) · " + r.retenus + " retenu(s) · " + r.non_retenus + " non retenu(s)");
      charger();
    } catch (e) {
      setMsg(e.message);
    } finally {
      setAttente(false);
    }
  }

  if (erreur) return <p className="erreur">{erreur}</p>;
  if (!d) return <p className="aide">Chargement...</p>;

  const t = d.totaux;
  const maxJour = Math.max(1, ...d.par_jour.map((j) => j.recus));
  const maxCat = Math.max(1, ...d.par_categorie.map((c) => c.nombre));

  return (
    <>
      <div className="entete">
        <div>
          <h1>Tableau de bord</h1>
          <p>Vue d'ensemble des 7 derniers jours</p>
        </div>
        <button className="principal" disabled={attente} onClick={traiter}>
          {attente ? "Traitement..." : "Traiter maintenant"}
        </button>
      </div>
      {msg && <div className="carte-b">{msg}</div>}
      {d.alertes_ouvertes > 0 && (
        <div className="bandeau-alerte">
          {d.alertes_ouvertes} alerte(s) de sécurité à examiner.{" "}
          <button className="lien" onClick={() => aller("alertes")}>Voir les alertes</button>
        </div>
      )}
      <div className="kpis">
        <div className="kpi"><span>Emails reçus</span><b>{t.recus}</b></div>
        <div className="kpi vert"><span>Retenus</span><b>{t.retenus}</b></div>
        <div className="kpi ambre"><span>À valider</span><b>{t.a_valider}</b></div>
        <div className="kpi"><span>Non retenus</span><b>{t.non_retenus}</b></div>
        <div className="kpi rouge"><span>Bloqués</span><b>{t.bloques}</b></div>
      </div>
      <div className="grille">
        <div className="carte-b">
          <h2>Emails par jour</h2>
          <div className="barres">
            {d.par_jour.map((j) => (
              <div className="col" key={j.jour}>
                {j.recus}
                <i style={{ height: (j.recus / maxJour) * 100 + "%" }} />
                {j.jour.slice(8, 10) + "/" + j.jour.slice(5, 7)}
              </div>
            ))}
          </div>
        </div>
        <div className="carte-b">
          <h2>Par catégorie</h2>
          {d.par_categorie.length === 0 && <p className="aide">Aucun email classé.</p>}
          {d.par_categorie.map((c) => (
            <div className="ligne-cat" key={c.code}>
              <span>{c.nom}</span>
              <div><i style={{ width: (c.nombre / maxCat) * 100 + "%" }} /></div>
              <em>{c.nombre}</em>
            </div>
          ))}
        </div>
      </div>
      <div className="carte-b">
        <h2>Dernières actions</h2>
        <div className="tableau-w">
          <table>
            <thead><tr><th>Date</th><th>Client</th><th>Objet</th><th>Catégorie</th><th>Statut</th></tr></thead>
            <tbody>
              {d.derniers.map((e) => (
                <tr key={e.id}>
                  <td>{formatDate(e.date)}</td>
                  <td>{e.client || "—"}</td>
                  <td>{e.objet}</td>
                  <td>{e.categorie || "—"}</td>
                  <td><span className={"badge " + classeDecision(e.decision)}>{libelleDecision(e.decision)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
