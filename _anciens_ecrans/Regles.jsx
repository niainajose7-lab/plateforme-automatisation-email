import { useCallback, useEffect, useState } from "react";
import { appeler } from "./api";

const TYPES = {
  facture: "une facture",
  reclamation: "une reclamation",
  demande: "une demande",
  autre: "un autre type d'email",
};

function quand(c) {
  if (c.champ === "categorie" && TYPES[c.valeur]) return "l'email est " + TYPES[c.valeur];
  return "l'email " + c.champ + " " + c.operateur + " ' " + c.valeur + " '";
}

export default function Regles({ jeton, onDeconnexion }) {
  const [boites, setBoites] = useState([]);
  const [regles, setRegles] = useState([]);
  const [erreur, setErreur] = useState("");
  const [info, setInfo] = useState("");
  const [charge, setCharge] = useState(false);
  const [type, setType] = useState("facture");
  const [transfert, setTransfert] = useState("");
  const [validation, setValidation] = useState(false);
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
    appeler("/emails/", { jeton }).then(setBoites).catch(gerer);
    charger();
  }, [jeton, gerer, charger]);

  async function creer(e) {
    e.preventDefault();
    setErreur("");
    setInfo("");
    if (!transfert.trim()) {
      setErreur("Indique au moins une adresse email.");
      return;
    }
    if (boites.length === 0) {
      setErreur("Connecte d'abord une boite Gmail.");
      return;
    }
    setAttente(true);
    try {
      await appeler("/regles/", {
        jeton,
        methode: "POST",
        corps: {
          boite_mail_id: boites[0].id,
          nom: "Transferer " + TYPES[type],
          condition: { champ: "categorie", operateur: "egal", valeur: type },
          transfert_vers: transfert.trim(),
          validation,
        },
      });
      setTransfert("");
      setValidation(false);
      setInfo("Regle creee. Elle s'applique a chaque nouvel email de ce type.");
      charger();
    } catch (err) {
      gerer(err);
    } finally {
      setAttente(false);
    }
  }

  async function basculer(r) {
    setErreur("");
    setInfo("");
    try {
      await appeler("/regles/" + r.id, { jeton, methode: "PATCH", corps: { actif: !r.actif } });
      charger();
    } catch (err) {
      gerer(err);
    }
  }

  async function supprimer(r) {
    if (!window.confirm("Supprimer cette regle ?")) return;
    setErreur("");
    setInfo("");
    try {
      await appeler("/regles/" + r.id, { jeton, methode: "DELETE" });
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
          <strong>Attention.</strong> {erreur}
        </div>
      )}

      <section className="bloc">
        <h2>A quoi servent les regles ?</h2>
        <p className="aide">
          Une regle est une consigne simple : <strong>quand</strong> un email est d'un certain
          type, <strong>alors</strong> la plateforme en envoie une copie a la personne de ton choix.
          Elle le fait toute seule, pour chaque nouvel email.
        </p>
      </section>

      <section className="bloc">
        <h2>Nouvelle regle</h2>
        <form onSubmit={creer} className="formulaire">
          <label>
            1. Quand un email est de type :
            <select value={type} onChange={(e) => setType(e.target.value)}>
              {Object.keys(TYPES).map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          {type === "autre" && (
            <p className="aide">Attention : ce type attrape beaucoup d'emails (notifications, publicites...).</p>
          )}
          <label>
            2. Alors envoyer une copie a (plusieurs adresses possibles, separees par une virgule) :
            <input
              type="text"
              value={transfert}
              onChange={(e) => setTransfert(e.target.value)}
              placeholder="adresse1@exemple.com, adresse2@exemple.com"
            />
          </label>
          <label>
            <input type="checkbox" checked={validation} onChange={(e) => setValidation(e.target.checked)} />{" "}
            3. Me demander mon accord avant d'envoyer (facultatif)
          </label>
          {info && <p className="succes">{info}</p>}
          <div>
            <button type="submit" disabled={attente}>
              {attente ? "Patientez..." : "Creer la regle"}
            </button>
          </div>
        </form>
      </section>

      <section className="bloc">
        <h2>Mes regles</h2>
        {!charge && !erreur ? (
          <p className="aide">Chargement...</p>
        ) : regles.length === 0 ? (
          <p className="aide">Aucune regle pour le moment.</p>
        ) : (
          <div className="liste">
            {regles.map((r) => (
              <div className="regle" key={r.id}>
                <div>
                  <strong>Quand {quand(r.condition)}</strong>
                  <div className="aide">
                    {r.transfert_vers
                      ? "Alors envoyer une copie a " + r.transfert_vers + (r.validation ? " (apres votre accord)" : "")
                      : "Alors : aucune action externe"}
                  </div>
                </div>
                <div className="actions">
                  <span className={"badge " + (r.actif ? "ok" : "")}>{r.actif ? "Active" : "Desactivee"}</span>
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
