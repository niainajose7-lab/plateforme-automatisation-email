import { useCallback, useEffect, useState } from "react";
import { appeler } from "./api";
import { libelleDecision, classeDecision, formatDate } from "./libelles";

const pct = (c) => (c == null ? null : Math.round(c > 1 ? c : c * 100));

function resume(info) {
  if (!info || typeof info !== "object") return "—";
  const l = Object.entries(info)
    .filter(([, v]) => v !== null && v !== "" && typeof v !== "object")
    .slice(0, 3)
    .map(([k, v]) => k + " : " + v);
  return l.length ? l.join(" · ") : "—";
}

function Detail({ id, jeton, retour, onDeconnexion }) {
  const [e, setE] = useState(null);
  const [erreur, setErreur] = useState("");
  const [refus, setRefus] = useState(false);
  const [motif, setMotif] = useState("");
  const [attente, setAttente] = useState(false);

  const charger = useCallback(async () => {
    try {
      setE(await appeler("/admin/emails/" + id, { jeton }));
    } catch (x) {
      if (x.statut === 401) onDeconnexion();
      else setErreur(x.message);
    }
  }, [id, jeton, onDeconnexion]);
  useEffect(() => { charger(); }, [charger]);

  async function decider(accepter) {
    setAttente(true);
    setErreur("");
    try {
      await appeler("/admin/emails/" + id + "/valider", { methode: "POST", jeton, corps: { accepter, motif } });
      setRefus(false);
      await charger();
    } catch (x) {
      setErreur(x.message);
    } finally {
      setAttente(false);
    }
  }

  if (!e) return <p className={erreur ? "erreur" : "aide"}>{erreur || "Chargement..."}</p>;
  const conf = pct(e.confiance);
  const seuil = Math.round(e.seuil * 100);

  return (
    <>
      <div className="entete">
        <div>
          <h1>Lecture d'un email</h1>
          <p>{e.expediteur} · {formatDate(e.date)}</p>
        </div>
        <button className="secondaire" onClick={retour}>← Retour au suivi</button>
      </div>
      <div className="grille">
        <div className="carte-b">
          <h2>{e.objet}</h2>
          <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{e.corps || "(message vide)"}</p>
          {e.pieces_jointes.map((p, i) => (
            <div key={i} style={{ marginTop: 14, padding: 12, border: "1px solid #E4E7EC", borderRadius: 10 }}>
              <b>{p.nom}</b> <span className="info">{p.type} · {p.statut}</span>
              {p.texte && <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, background: "#F4F6FA", padding: 10, borderRadius: 8, maxHeight: 200, overflow: "auto" }}>{p.texte}</pre>}
            </div>
          ))}
        </div>
        <div className="carte-b">
          <h2>Analyse</h2>
          <p>Catégorie : <b>{e.categorie_nom || "—"}</b></p>
          <p>Client : <b>{e.client || "—"}</b></p>
          <p>Statut : <span className={"badge " + classeDecision(e.decision)}>{libelleDecision(e.decision)}</span></p>
          {e.motif && <p className="info">Motif : {e.motif}</p>}
          {conf !== null && (
            <>
              <p className="info">Confiance {conf} % · seuil {seuil} %</p>
              <div style={{ position: "relative", height: 10, background: "#EEF1F6", borderRadius: 99 }}>
                <div style={{ width: conf + "%", height: "100%", background: conf >= seuil ? "#0B6B3A" : "#8A5300", borderRadius: 99 }} />
                <div style={{ position: "absolute", left: seuil + "%", top: -4, width: 2, height: 18, background: "#0F172A" }} />
              </div>
            </>
          )}
          <p className="info" style={{ marginTop: 14 }}>Informations clés : {resume(e.informations)}</p>
          {erreur && <p className="erreur">{erreur}</p>}
          {e.decision === "a_valider" && (
            <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 10 }}>
              {!refus && (
                <div style={{ display: "flex", gap: 10 }}>
                  <button className="principal" disabled={attente} onClick={() => decider(true)}>Accepter</button>
                  <button className="contour rouge" onClick={() => setRefus(true)}>Refuser</button>
                </div>
              )}
              {refus && (
                <>
                  <label>Motif du refus (envoyé au client)
                    <textarea rows="3" value={motif} onChange={(x) => setMotif(x.target.value)} />
                  </label>
                  <div style={{ display: "flex", gap: 10 }}>
                    <button className="principal" disabled={attente} onClick={() => decider(false)}>Confirmer le refus</button>
                    <button className="secondaire" onClick={() => setRefus(false)}>Annuler</button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default function SuiviEmails({ jeton, onDeconnexion }) {
  const vide = { q: "", decision: "", categorie: "", client_id: "", debut: "", fin: "" };
  const [f, setF] = useState(vide);
  const [page, setPage] = useState(1);
  const [d, setD] = useState(null);
  const [cats, setCats] = useState([]);
  const [clients, setClients] = useState([]);
  const [erreur, setErreur] = useState("");
  const [sel, setSel] = useState(null);

  useEffect(() => {
    appeler("/admin/categories", { jeton }).then(setCats).catch(() => {});
    appeler("/admin/clients", { jeton }).then((r) => setClients(r.clients)).catch(() => {});
  }, [jeton]);

  const charger = useCallback(async () => {
    const p = new URLSearchParams({ page, taille: 12 });
    Object.entries(f).forEach(([k, v]) => v && p.set(k, v));
    try {
      setD(await appeler("/admin/emails?" + p.toString(), { jeton }));
      setErreur("");
    } catch (x) {
      if (x.statut === 401) onDeconnexion();
      else setErreur(x.message);
    }
  }, [f, page, jeton, onDeconnexion]);
  useEffect(() => { charger(); }, [charger]);

  function maj(cle, valeur) {
    setF({ ...f, [cle]: valeur });
    setPage(1);
  }

  if (sel) return <Detail id={sel} jeton={jeton} onDeconnexion={onDeconnexion} retour={() => { setSel(null); charger(); }} />;

  const pages = d ? Math.max(1, Math.ceil(d.total / d.taille)) : 1;
  return (
    <>
      <div className="entete">
        <div>
          <h1>Suivi des emails</h1>
          <p>Tous les emails reçus, avec la décision de la plateforme</p>
        </div>
      </div>
      <div className="carte-b">
        <div className="filtres">
          <label>Recherche<input value={f.q} onChange={(x) => maj("q", x.target.value)} placeholder="Objet ou expéditeur" /></label>
          <label>Statut
            <select value={f.decision} onChange={(x) => maj("decision", x.target.value)}>
              <option value="">Tous</option>
              <option value="retenu">Retenu</option>
              <option value="a_valider">À valider</option>
              <option value="non_retenu">Non retenu</option>
              <option value="bloque">Bloqué</option>
              <option value="rejete">Rejeté</option>
              <option value="inconnu">Inconnu</option>
            </select>
          </label>
          <label>Catégorie
            <select value={f.categorie} onChange={(x) => maj("categorie", x.target.value)}>
              <option value="">Toutes</option>
              {cats.map((c) => <option key={c.code} value={c.code}>{c.nom}</option>)}
            </select>
          </label>
          <label>Client
            <select value={f.client_id} onChange={(x) => maj("client_id", x.target.value)}>
              <option value="">Tous</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
            </select>
          </label>
          <label>Du<input type="date" value={f.debut} onChange={(x) => maj("debut", x.target.value)} /></label>
          <label>Au<input type="date" value={f.fin} onChange={(x) => maj("fin", x.target.value)} /></label>
          <button className="secondaire" onClick={() => { setF(vide); setPage(1); }}>Réinitialiser</button>
        </div>
      </div>
      {erreur && <p className="erreur">{erreur}</p>}
      <div className="carte-b">
        <div className="tableau-w">
          <table>
            <thead>
              <tr><th>Date</th><th>Client</th><th>Objet</th><th>Catégorie</th><th>Confiance</th><th>Informations clés</th><th>Statut</th><th></th></tr>
            </thead>
            <tbody>
              {d && d.emails.map((e) => (
                <tr key={e.id} className="clic" onClick={() => setSel(e.id)}>
                  <td>{formatDate(e.date)}</td>
                  <td>{e.client || "—"}</td>
                  <td>{e.objet}</td>
                  <td>{e.categorie || "—"}</td>
                  <td>{pct(e.confiance) !== null ? pct(e.confiance) + " %" : "—"}</td>
                  <td className="info">{resume(e.informations)}</td>
                  <td>
                    <span className={"badge " + classeDecision(e.decision)}>{libelleDecision(e.decision)}</span>
                    {e.motif && <div className="info">{e.motif}</div>}
                  </td>
                  <td><button className={"contour " + (e.decision === "a_valider" ? "bleu" : "")}>{e.decision === "a_valider" ? "Valider" : "Voir"}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {d && d.emails.length === 0 && <p className="aide">Aucun email ne correspond à ces filtres.</p>}
        <div className="pagination">
          <span>{d ? d.total : 0} email(s)</span>
          <button className="secondaire" disabled={page <= 1} onClick={() => setPage(page - 1)}>Précédent</button>
          <span>Page {page} / {pages}</span>
          <button className="secondaire" disabled={page >= pages} onClick={() => setPage(page + 1)}>Suivant</button>
        </div>
      </div>
    </>
  );
}
