import { useCallback, useEffect, useState } from "react";
import { appeler } from "./api";
import { formatDate } from "./libelles";

export default function Alertes({ jeton, onDeconnexion }) {
  const [liste, setListe] = useState(null);
  const [erreur, setErreur] = useState("");

  const charger = useCallback(async () => {
    try {
      setListe(await appeler("/admin/alertes", { jeton }));
    } catch (x) {
      if (x.statut === 401) onDeconnexion();
      else setErreur(x.message);
    }
  }, [jeton, onDeconnexion]);
  useEffect(() => { charger(); }, [charger]);

  async function traiter(id) {
    try {
      await appeler("/admin/alertes/" + id + "/traiter", { methode: "POST", jeton });
      charger();
    } catch (x) {
      setErreur(x.message);
    }
  }

  if (!liste) return <p className={erreur ? "erreur" : "aide"}>{erreur || "Chargement..."}</p>;

  return (
    <>
      <div className="entete">
        <div>
          <h1>Alertes de sécurité</h1>
          <p>Emails dangereux détectés par la plateforme</p>
        </div>
      </div>
      {erreur && <p className="erreur">{erreur}</p>}
      {liste.length === 0 && <div className="carte-b">Aucune alerte.</div>}
      {liste.map((a) => (
        <div className="carte-b" key={a.id} style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <span className={"badge " + (a.traitee ? "" : "alerte")}>{a.traitee ? "Traitée" : "À examiner"}</span>{" "}
            <b>{a.type === "hameconnage" ? "Hameçonnage" : a.type === "piece_jointe" ? "Pièce jointe à risque" : a.type}</b>
            <div style={{ marginTop: 6 }}>{a.objet}</div>
            <div className="info">{a.expediteur} · {formatDate(a.date)}</div>
            <div className="info">{a.details}</div>
          </div>
          {!a.traitee && <button className="contour bleu" onClick={() => traiter(a.id)}>Marquer comme traitée</button>}
        </div>
      ))}
    </>
  );
}
