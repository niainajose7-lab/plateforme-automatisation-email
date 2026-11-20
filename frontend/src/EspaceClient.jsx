import { useCallback, useEffect, useRef, useState } from "react";
import { appeler } from "./api";
import { libelleDecision, classeDecision, formatDate } from "./libelles";

const MAX = 5 * 1024 * 1024;

function lireFichier(fichier) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",")[1] || "");
    r.onerror = () => reject(new Error("Fichier illisible"));
    r.readAsDataURL(fichier);
  });
}

export default function EspaceClient({ jeton, moi, onDeconnexion }) {
  const [emails, setEmails] = useState([]);
  const [objet, setObjet] = useState("");
  const [corps, setCorps] = useState("");
  const [fichier, setFichier] = useState(null);
  const [msg, setMsg] = useState("");
  const [erreur, setErreur] = useState("");
  const [attente, setAttente] = useState(false);
  const champFichier = useRef(null);
  const actif = !!moi.actif && !!moi.identifiant;

  const charger = useCallback(async () => {
    if (!moi.identifiant) return;
    try {
      setEmails(await appeler("/client/emails", { jeton }));
    } catch (x) {
      if (x.statut === 401) onDeconnexion();
    }
  }, [jeton, moi.identifiant, onDeconnexion]);

  useEffect(() => {
    charger();
    const t = setInterval(charger, 10000);
    return () => clearInterval(t);
  }, [charger]);

  async function envoyer(e) {
    e.preventDefault();
    setErreur("");
    setMsg("");
    if (fichier && fichier.size > MAX) {
      setErreur("Pièce jointe trop volumineuse (5 Mo maximum)");
      return;
    }
    setAttente(true);
    try {
      const donnees = { objet, corps };
      if (fichier) {
        donnees.piece_jointe = {
          nom: fichier.name,
          type: fichier.type || "application/octet-stream",
          donnees_base64: await lireFichier(fichier),
        };
      }
      await appeler("/client/envoyer", { methode: "POST", jeton, corps: donnees });
      setMsg("Votre email a été envoyé à la plateforme. Vous serez notifié du résultat.");
      setObjet("");
      setCorps("");
      setFichier(null);
      if (champFichier.current) champFichier.current.value = "";
      setTimeout(charger, 4000);
    } catch (x) {
      setErreur(x.message);
    } finally {
      setAttente(false);
    }
  }

  function corriger(e) {
    setObjet((e.objet || "").replace(/^(\[Transfert\]|\[Notification\])\s*/, ""));
    setCorps("");
    setMsg("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div style={{ minHeight: "100vh" }}>
      <header style={{ background: "#0B1B33", color: "#fff", padding: "16px 36px", display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div className="logo">
          <div className="pastille">A</div>
          <div><b>AutoMail</b><small>Espace client</small></div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ textAlign: "right", fontSize: 13, lineHeight: 1.35 }}>
            <div style={{ fontWeight: 600 }}>{moi.nom}</div>
            <div style={{ color: "#9DB0CF" }}>Identifiant {moi.identifiant || "—"}</div>
          </div>
          <button className="deco" style={{ background: "transparent", border: "1px solid #3A5078", color: "#fff", borderRadius: 8, padding: "7px 14px", cursor: "pointer" }} onClick={onDeconnexion}>Déconnexion</button>
        </div>
      </header>

      <main style={{ maxWidth: 1240, margin: "0 auto", padding: "28px 36px", display: "flex", flexWrap: "wrap", gap: 18, alignItems: "flex-start" }}>
        {!moi.identifiant && (
          <div className="bandeau-alerte" style={{ flex: "1 1 100%" }}>Votre compte n'est lié à aucun client. Contactez l'administrateur.</div>
        )}
        {moi.identifiant && !moi.actif && (
          <div className="bandeau-alerte" style={{ flex: "1 1 100%" }}>Votre compte client est désactivé : vous ne pouvez plus envoyer d'emails. Contactez l'administrateur.</div>
        )}

        {actif && (
          <form className="carte-b" onSubmit={envoyer} style={{ flex: "2 1 320px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
            <h2>Envoyer un email</h2>
            <p className="aide">Votre message est analysé et classé automatiquement. Vous serez notifié du résultat.</p>
            <label>Objet<input value={objet} onChange={(x) => setObjet(x.target.value)} placeholder="Ex. Facture mars" required /></label>
            <label>Message<textarea rows="6" value={corps} onChange={(x) => setCorps(x.target.value)} placeholder="Votre message..." required /></label>
            <label>Pièce jointe (PDF, image — 5 Mo max)
              <input type="file" ref={champFichier} onChange={(x) => setFichier(x.target.files[0] || null)} />
            </label>
            {erreur && <p className="erreur">{erreur}</p>}
            {msg && <p style={{ color: "#0B6B3A", margin: 0 }}>{msg}</p>}
            <button className="principal" type="submit" disabled={attente}>{attente ? "Envoi..." : "Envoyer à la plateforme"}</button>
          </form>
        )}

        <section className="carte-b" style={{ flex: "3 1 480px", minWidth: 0 }}>
          <h2>Mes emails</h2>
          {emails.length === 0 && <p className="aide">Aucun email pour le moment.</p>}
          <div className="tableau-w">
            <table>
              <thead><tr><th>Date</th><th>Objet</th><th>Catégorie</th><th>Statut</th><th></th></tr></thead>
              <tbody>
                {emails.map((e) => (
                  <tr key={e.id}>
                    <td>{formatDate(e.date)}</td>
                    <td>{e.objet}</td>
                    <td>{e.categorie || "—"}</td>
                    <td>
                      <span className={"badge " + classeDecision(e.decision)}>{libelleDecision(e.decision)}</span>
                      {e.motif && <div className="info">{e.motif}</div>}
                    </td>
                    <td>{actif && e.decision === "non_retenu" && <button className="contour bleu" onClick={() => corriger(e)}>Corriger et renvoyer</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
