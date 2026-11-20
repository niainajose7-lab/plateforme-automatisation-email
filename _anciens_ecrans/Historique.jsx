import { useCallback, useEffect, useState } from "react";
import { appeler } from "./api";

const STATUTS = {
  succes: ["Reussi", "ok"],
  echec: ["Echec", "alerte"],
  ignore: ["Ignore", ""],
  refuse: ["Refuse", ""],
  en_attente_validation: ["A valider", "a_valider"],
};

function quand(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("fr-FR");
}

export default function Historique({ jeton, onDeconnexion }) {
  const [lignes, setLignes] = useState([]);
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(true);

  const gerer = useCallback(
    (err) => {
      if (err.statut === 401) onDeconnexion();
      else setErreur(err.message);
    },
    [onDeconnexion]
  );

  useEffect(() => {
    let actif = true;
    appeler("/emails/", { jeton })
      .then(async (boites) => {
        const toutes = [];
        for (const b of boites) {
          const l = await appeler("/emails/" + b.id + "/historique", { jeton });
          toutes.push(...l);
        }
        toutes.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
        if (actif) setLignes(toutes);
      })
      .catch((err) => actif && gerer(err))
      .finally(() => actif && setChargement(false));
    return () => {
      actif = false;
    };
  }, [jeton, gerer]);

  return (
    <section className="bloc">
      <h2>Historique des actions</h2>
      <p className="aide">Chaque action decidee par une regle : quand, sur quel email, avec quel resultat.</p>
      {erreur && <p className="erreur">{erreur}</p>}
      {chargement ? (
        <p className="aide">Chargement...</p>
      ) : lignes.length === 0 ? (
        <p className="aide">Aucune action pour le moment.</p>
      ) : (
        <div className="defile">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Email</th>
                <th>Categorie</th>
                <th>Regle</th>
                <th>Resultat</th>
              </tr>
            </thead>
            <tbody>
              {lignes.map((l, i) => {
                const [texte, classe] = STATUTS[l.statut] || [l.statut, ""];
                return (
                  <tr key={i}>
                    <td className="discret">{quand(l.date)}</td>
                    <td>{l.objet || "(sans objet)"}</td>
                    <td>{l.categorie || "-"}</td>
                    <td>{l.regle}</td>
                    <td>
                      <span className={"badge " + classe}>{texte}</span>
                      {l.statut === "succes" && l.destinataire && (
                        <div className="aide">vers {l.destinataire}</div>
                      )}
                      {l.details && l.statut !== "succes" && <div className="aide">{l.details}</div>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
