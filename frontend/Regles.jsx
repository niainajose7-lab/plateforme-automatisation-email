import { useCallback, useEffect, useState } from "react";
import { appeler } from "./api";

const CHAMPS = {
  objet: "L'objet",
  expediteur: "L'expediteur",
  extrait: "Le texte",
  categorie: "La categorie",
};
const OPERATEURS = {
  contient: "contient",
  egal: "est egal a",
  commence_par: "commence par",
};
const CATEGORIES = ["facture", "reclamation", "demande", "autre"];

function phrase(c) {
  return (CHAMPS[c.champ] || c.champ) + " " + (OPERATEURS[c.operateur] || c.operateur) + " « " + c.valeur + " »";
}

export default function Regles({ jeton, onDeconnexion }) {
  const [boites, setBoites] = useState([]);
  const [regles, setRegles] = useState([]);
  const [erreur, setErreur] = useState("");
  const [info, setInfo] = useState("");
  const [charge, setCharge] = useState(false);

  const [boiteId, setBoiteId] = useState("");
  const [nom, setNom] = useState("");
  const [champ, setChamp] = useState("categorie");
  const [operateur, setOperateur] = useState("egal");
  const [valeur, setValeur] = useState("facture");
  const [transfert, setTransfert] = useState("");
  const [attente, setAttente] = useState(false);

  const gerer = useCallback(
    (err) => {
      if (err.statut === 401) onDeconnexion();
      else setErreur(err.message);
    },
    [onDeconnexion]
  );

  const charger = useCallback(() => {
    appeler("/regles/", { jeton })
      .then((liste) => {
        setRegles(liste);
        setErreur("");
        setCharge(true);
      })
      .catch(gerer);
  }, [jeton, gerer]);

  useEffect(() => {
    appeler("/emails/", { jeton })
      .then((liste) => {
        setBoites(liste);
        if (liste.length > 0) setBoiteId((actuel) => actuel || liste[0].id);
      })
      .catch(gerer);
    charger();
  }, [jeton, gerer, charger]);

  function changerChamp(nouveau) {
    setChamp(nouveau);
    // Pour la categorie, la valeur est choisie dans une liste
    if (nouveau === "categorie") {
      setOperateur("egal");
      setValeur("facture");
    } else {
      setValeur("");
    }
  }

  async function creer(e) {
    e.preventDefault();
    setErreur("");
    setInfo("");
    setAttente(true);
    try {
      await appeler("/regles/", {
        jeton,
        methode: "POST",
        corps: {
          boite_mail_id: boiteId,
          nom,
          condition: { champ, operateur, valeur },
          transfert_vers: transfert.trim() || null,
        },
      });
      setNom("");
      setTransfert("");
      if (champ !== "categorie") setValeur("");
      setInfo("Regle creee.");
      charger();
    } catch (err) {
      gerer(err);
    } finally {
      setAttente(false);
    }
  }

  async function basculer(regle) {
    setErreur("");
    setInfo("");
    try {
      await appeler("/regles/" + regle.id, {
        jeton,
        methode: "PATCH",
        corps: { actif: !regle.actif },
      });
      charger();
    } catch (err) {
      gerer(err);
    }
  }

  async function supprimer(regle) {
    if (!window.confirm("Supprimer la regle « " + regle.nom + " » ?")) return;
    setErreur("");
    setInfo("");
    try {
      await appeler("/regles/" + regle.id, { jeton, methode: "DELETE" });
      setInfo("Regle supprimee.");
      charger();
    } catch (err) {
      gerer(err);
    }
  }

  return (
    <>
      {erreur && (
        <div className="alerte-bloc">
          <strong>Impossible d'afficher les règles.</strong> {erreur}
        </div>
      )}
      <section className="bloc">
        <h2>Nouvelle règle</h2>
        <p className="aide">
          Une regle dit : « si un email correspond a cette condition, alors la
          plateforme le retient et execute l'action choisie ».
        </p>
        {boites.length === 0 ? (
          <p className="aide">Connectez d'abord une boite Gmail (onglet Suivi).</p>
        ) : (
          <form className="formulaire" onSubmit={creer}>
            {boites.length > 1 && (
              <label>
                Boite mail
                <select value={boiteId} onChange={(e) => setBoiteId(e.target.value)}>
                  {boites.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.adresse}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Nom de la regle
              <input
                value={nom}
                onChange={(e) => setNom(e.target.value)}
                placeholder="Ex : Transferer les factures"
                required
              />
            </label>

            <div className="trio">
              <label>
                Si
                <select value={champ} onChange={(e) => changerChamp(e.target.value)}>
                  {Object.entries(CHAMPS).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Condition
                <select
                  value={operateur}
                  onChange={(e) => setOperateur(e.target.value)}
                  disabled={champ === "categorie"}
                >
                  {Object.entries(OPERATEURS).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Valeur
                {champ === "categorie" ? (
                  <select value={valeur} onChange={(e) => setValeur(e.target.value)}>
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    value={valeur}
                    onChange={(e) => setValeur(e.target.value)}
                    required
                  />
                )}
              </label>
            </div>

            <label>
              Alors transferer l'email a (facultatif)
              <input
                type="email"
                value={transfert}
                onChange={(e) => setTransfert(e.target.value)}
                placeholder="adresse@exemple.com"
              />
            </label>

            {info && <p className="succes">{info}</p>}
            <div>
              <button type="submit" disabled={attente}>
                {attente ? "Patientez..." : "Creer la regle"}
              </button>
            </div>
          </form>
        )}
      </section>

      <section className="bloc">
        <h2>Mes règles</h2>
        {!charge && !erreur ? (
          <p className="aide">Chargement…</p>
        ) : regles.length === 0 ? (
          <p className="aide">Aucune règle pour le moment.</p>
        ) : (
          <div className="liste">
            {regles.map((r) => (
              <div className="regle" key={r.id}>
                <div>
                  <strong>{r.nom}</strong>
                  <div className="aide">Si {phrase(r.condition)}</div>
                  <div className="aide">
                    {r.transfert_vers
                      ? "Alors transferer a " + r.transfert_vers
                      : "Alors : retenir l'email (aucune action externe)"}
                  </div>
                </div>
                <div className="actions">
                  <span className={"badge " + (r.actif ? "ok" : "")}>
                    {r.actif ? "Active" : "Desactivee"}
                  </span>
                  <button className="secondaire" onClick={() => basculer(r)}>
                    {r.actif ? "Desactiver" : "Activer"}
                  </button>
                  <button className="danger" onClick={() => supprimer(r)}>
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
