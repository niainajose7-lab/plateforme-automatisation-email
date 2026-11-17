import { useCallback, useEffect, useState } from "react";
import { API, appeler } from "./api";

const LIBELLES_DECISION = {
  retenu: "Retenu",
  a_valider: "A valider",
  non_retenu: "Non retenu",
  en_attente: "En attente",
};

function formaterDate(iso) {
  if (!iso) return "";
  const [a, m, j] = iso.split("-");
  return j + "/" + m + "/" + a;
}

function resumeFacture(f) {
  if (!f) return "-";
  const morceaux = [];
  if (f.numero) morceaux.push("N° " + f.numero);
  if (f.montant && f.montant.valeur != null)
    morceaux.push(Number(f.montant.valeur).toLocaleString("fr-FR") + " " + (f.montant.texte || "").replace(/[\d\s.,]+/, ""));
  if (f.echeance) morceaux.push("echeance " + formaterDate(f.echeance));
  else if (f.date) morceaux.push("du " + formaterDate(f.date));
  return morceaux.length ? morceaux.join(" · ") : "-";
}

export default function Tableau({ jeton, onDeconnexion }) {
  const [boites, setBoites] = useState([]);
  const [boiteId, setBoiteId] = useState("");
  const [emails, setEmails] = useState([]);
  const [erreur, setErreur] = useState("");
  const [info, setInfo] = useState("");
  const [traitement, setTraitement] = useState(false);

  // Session expiree : retour a la page de connexion
  const gerer = useCallback(
    (err) => {
      if (err.statut === 401) onDeconnexion();
      else setErreur(err.message);
    },
    [onDeconnexion]
  );

  useEffect(() => {
    appeler("/emails/", { jeton })
      .then((liste) => {
        setBoites(liste);
        if (liste.length > 0) setBoiteId((actuel) => actuel || liste[0].id);
      })
      .catch(gerer);
  }, [jeton, gerer]);

  useEffect(() => {
    if (!boiteId) return undefined;
    let actif = true;
    function charger() {
      appeler("/emails/" + boiteId + "/suivi", { jeton })
        .then((liste) => {
          if (actif) {
            setEmails(liste);
            setErreur("");
          }
        })
        .catch((err) => actif && gerer(err));
    }
    charger();
    const minuteur = setInterval(charger, 10000); // actualisation automatique
    return () => {
      actif = false;
      clearInterval(minuteur);
    };
  }, [boiteId, jeton, gerer]);

  const boite = boites.find((b) => b.id === boiteId);

  async function traiterMaintenant() {
    setErreur("");
    setInfo("");
    setTraitement(true);
    try {
      const r = await appeler("/emails/" + boiteId + "/traiter", { jeton, methode: "POST" });
      setInfo(
        r.nouveaux + " nouveau(x) email(s), " + r.retenus + " retenu(s), " + r.non_retenus + " non retenu(s)."
      );
      setEmails(await appeler("/emails/" + boiteId + "/suivi", { jeton }));
    } catch (err) {
      gerer(err);
    } finally {
      setTraitement(false);
    }
  }

  function connecterGmail() {
    window.location.href = API + "/auth/gmail/connect?token=" + encodeURIComponent(jeton);
  }

  return (
    <>
      <section className="bloc">
        <div className="ligne">
          <h2>Boites mail</h2>
          <button onClick={connecterGmail}>Connecter une boite Gmail</button>
        </div>
        {boites.length === 0 ? (
          <p className="aide">Aucune boite connectee pour le moment.</p>
        ) : (
          <div className="ligne">
            <select value={boiteId} onChange={(e) => setBoiteId(e.target.value)}>
              {boites.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.adresse}
                </option>
              ))}
            </select>
            {boite && (
              <span className={"badge " + (boite.statut === "actif" ? "ok" : "alerte")}>
                {boite.statut === "actif" ? "Connectee" : "A reconnecter"}
              </span>
            )}
          </div>
        )}
      </section>

      <section className="bloc">
        <div className="ligne">
          <h2>Suivi des emails</h2>
          <button onClick={traiterMaintenant} disabled={!boiteId || traitement}>
            {traitement ? "Traitement..." : "Traiter maintenant"}
          </button>
        </div>
        {erreur && <p className="erreur">{erreur}</p>}
        {info && <p className="succes">{info}</p>}
        {emails.length === 0 ? (
          <p className="aide">Aucun email synchronise pour cette boite.</p>
        ) : (
          <div className="defile">
            <table>
              <thead>
                <tr>
                  <th>Objet</th>
                  <th>Expediteur</th>
                  <th>Categorie</th>
                  <th>Confiance</th>
                  <th>Donnees de la facture</th>
                  <th>Decision</th>
                </tr>
              </thead>
              <tbody>
                {emails.map((e, i) => (
                  <tr key={i}>
                    <td>{e.objet || "(sans objet)"}</td>
                    <td className="discret">{e.expediteur}</td>
                    <td>{e.categorie || "-"}</td>
                    <td>
                      {typeof e.confiance === "number" && e.confiance > 0
                        ? Math.round(e.confiance * 100) + " %"
                        : "-"}
                    </td>
                    <td className="discret-large">{resumeFacture(e.facture)}</td>
                    <td>
                      <span className={"badge " + (e.decision || "en_attente")}>
                        {LIBELLES_DECISION[e.decision] || "En attente"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="aide">Actualisation automatique toutes les 10 secondes.</p>
      </section>
    </>
  );
}
