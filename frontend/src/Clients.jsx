import { useCallback, useEffect, useState } from "react";
import { appeler } from "./api";

export default function Clients({ jeton, onDeconnexion }) {
  const [clients, setClients] = useState([]);
  const [prochain, setProchain] = useState("");
  const [inconnus, setInconnus] = useState([]);
  const [filtre, setFiltre] = useState("tous");
  const [q, setQ] = useState("");
  const [nom, setNom] = useState("");
  const [email, setEmail] = useState("");
  const [erreur, setErreur] = useState("");

  const charger = useCallback(async () => {
    try {
      const r = await appeler("/admin/clients", { jeton });
      setClients(r.clients);
      setProchain(r.prochain_identifiant);
      setInconnus(await appeler("/admin/inconnus", { jeton }));
    } catch (x) {
      if (x.statut === 401) onDeconnexion();
      else setErreur(x.message);
    }
  }, [jeton, onDeconnexion]);
  useEffect(() => { charger(); }, [charger]);

  async function appel(chemin, methode, corps) {
    setErreur("");
    try {
      await appeler(chemin, { methode, jeton, corps });
      await charger();
      return true;
    } catch (x) {
      setErreur(x.message);
      return false;
    }
  }

  async function ajouter(e) {
    e.preventDefault();
    if (await appel("/admin/clients", "POST", { nom, email })) {
      setNom("");
      setEmail("");
    }
  }

  const visibles = clients.filter(
    (c) =>
      (filtre === "tous" || (filtre === "actifs" ? c.actif : !c.actif)) &&
      (c.nom + c.email + c.identifiant).toLowerCase().includes(q.toLowerCase())
  );
  const nbActifs = clients.filter((c) => c.actif).length;

  return (
    <>
      <div className="entete">
        <div>
          <h1>Clients</h1>
          <p>Seuls les clients actifs peuvent écrire à la plateforme</p>
        </div>
      </div>
      {erreur && <p className="erreur">{erreur}</p>}
      <div className="grille">
        <div className="carte-b" style={{ flex: "3 1 520px" }}>
          <div className="filtres">
            <label style={{ flex: 1 }}>Recherche<input value={q} onChange={(x) => setQ(x.target.value)} placeholder="Rechercher un client..." /></label>
            <label>Statut
              <select value={filtre} onChange={(x) => setFiltre(x.target.value)}>
                <option value="tous">Tous</option>
                <option value="actifs">Actifs</option>
                <option value="desactives">Désactivés</option>
              </select>
            </label>
          </div>
          <div className="tableau-w">
            <table>
              <thead><tr><th>Identifiant</th><th>Nom</th><th>Email</th><th>Emails</th><th>Statut</th><th></th></tr></thead>
              <tbody>
                {visibles.map((c) => (
                  <tr key={c.id} style={{ color: c.actif ? undefined : "#667085" }}>
                    <td>{c.identifiant}</td>
                    <td><b>{c.nom}</b></td>
                    <td>{c.email}</td>
                    <td>{c.nb_emails}</td>
                    <td><span className={"badge " + (c.actif ? "ok" : "")}>{c.actif ? "Actif" : "Désactivé"}</span></td>
                    <td>
                      <button className={"contour " + (c.actif ? "rouge" : "bleu")} onClick={() => appel("/admin/clients/" + c.id, "PATCH", { actif: !c.actif })}>
                        {c.actif ? "Désactiver" : "Réactiver"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="info">{clients.length} client(s) · {nbActifs} actif(s) · {clients.length - nbActifs} désactivé(s)</p>
        </div>
        <div style={{ flex: "2 1 300px", display: "flex", flexDirection: "column", gap: 14 }}>
          <form className="carte-b" onSubmit={ajouter} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <h2>Nouveau client</h2>
            <label>Nom<input value={nom} onChange={(x) => setNom(x.target.value)} required /></label>
            <label>Adresse email<input type="email" value={email} onChange={(x) => setEmail(x.target.value)} required /></label>
            <p className="info">Identifiant attribué : <b>{prochain}</b></p>
            <button className="principal" type="submit">Enregistrer le client</button>
          </form>
          <div className="carte-b">
            <h2>Expéditeurs inconnus</h2>
            {inconnus.length === 0 && <p className="aide">Aucun expéditeur inconnu.</p>}
            {inconnus.map((u) => (
              <div key={u.adresse} style={{ padding: "10px 0", borderTop: "1px solid #EEF1F6" }}>
                <b>{u.adresse}</b>
                <div className="info">{u.nombre} email(s) · {u.dernier_objet}</div>
                <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                  <button className="contour bleu" onClick={() => appel("/admin/inconnus", "POST", { adresse: u.adresse, action: "ajouter" })}>Ajouter comme client</button>
                  <button className="contour" onClick={() => appel("/admin/inconnus", "POST", { adresse: u.adresse, action: "ignorer" })}>Ignorer</button>
                  <button className="contour rouge" onClick={() => appel("/admin/inconnus", "POST", { adresse: u.adresse, action: "bloquer" })}>Bloquer</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
