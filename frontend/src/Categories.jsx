import { useEffect, useState } from "react";
import { appeler } from "./api";

export default function Categories({ jeton, onDeconnexion }) {
  const [lignes, setLignes] = useState(null);
  const [erreur, setErreur] = useState("");
  const [ok, setOk] = useState("");

  useEffect(() => {
    appeler("/admin/categories", { jeton })
      .then((r) => setLignes(r.map((c) => ({ ...c, modifie: false }))))
      .catch((x) => (x.statut === 401 ? onDeconnexion() : setErreur(x.message)));
  }, [jeton, onDeconnexion]);

  function maj(id, champ, valeur) {
    setLignes(lignes.map((l) => (l.id === id ? { ...l, [champ]: valeur, modifie: true } : l)));
    setOk("");
  }

  async function sauver(l) {
    setErreur("");
    try {
      const r = await appeler("/admin/categories/" + l.id, {
        methode: "PATCH",
        jeton,
        corps: { seuil: l.seuil, service_nom: l.service_nom || "", service_email: l.service_email || "", actif: l.actif },
      });
      setLignes(lignes.map((x) => (x.id === l.id ? { ...r, modifie: false } : x)));
      setOk("Règle « " + l.nom + " » enregistrée.");
    } catch (x) {
      setErreur(x.message);
    }
  }

  if (!lignes) return <p className={erreur ? "erreur" : "aide"}>{erreur || "Chargement..."}</p>;

  return (
    <>
      <div className="entete">
        <div>
          <h1>Catégories et règles</h1>
          <p>Une règle par catégorie : quel seuil, quel service, quelle adresse</p>
        </div>
      </div>
      <div className="grille">
        <div className="carte-b"><h2>1. Reconnaître</h2><p className="aide">La plateforme lit l'email et ses pièces jointes, puis trouve la catégorie.</p></div>
        <div className="carte-b"><h2>2. Comparer</h2><p className="aide">Elle compare sa confiance au seuil de la catégorie.</p></div>
        <div className="carte-b"><h2>3. Décider</h2><p className="aide">Au-dessus du seuil : transfert au service. En dessous : à valider par l'administrateur.</p></div>
      </div>
      {erreur && <p className="erreur">{erreur}</p>}
      {ok && <div className="carte-b">{ok}</div>}
      <div className="carte-b">
        <div className="tableau-w">
          <table>
            <thead>
              <tr><th>Catégorie</th><th>Seuil de confiance</th><th>Service</th><th>Adresse du service</th><th>Active</th><th></th></tr>
            </thead>
            <tbody>
              {lignes.map((l) => (
                <tr key={l.id}>
                  <td><b>{l.nom}</b></td>
                  <td>
                    <input className="curseur" type="range" min="30" max="99" value={Math.round((l.seuil || 0.8) * 100)} onChange={(x) => maj(l.id, "seuil", Number(x.target.value) / 100)} />
                    {" "}<b>{Math.round((l.seuil || 0.8) * 100)} %</b>
                  </td>
                  <td><input value={l.service_nom || ""} onChange={(x) => maj(l.id, "service_nom", x.target.value)} placeholder="Aucun service" /></td>
                  <td><input value={l.service_email || ""} onChange={(x) => maj(l.id, "service_email", x.target.value)} placeholder="service@exemple.com" /></td>
                  <td><input type="checkbox" checked={!!l.actif} onChange={(x) => maj(l.id, "actif", x.target.checked)} /></td>
                  <td>{l.modifie && <button className="principal" onClick={() => sauver(l)}>Enregistrer</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="carte-b">
        <h2>Règles de sécurité (fixées dans le code)</h2>
        <ul style={{ margin: 0, paddingLeft: 18, lineHeight: 1.9 }}>
          <li>Hameçonnage ou pièce jointe à risque : email <b>bloqué</b> et alerte créée.</li>
          <li>Publicité ou newsletter : <b>non retenu</b>.</li>
          <li>Client désactivé : <b>rejeté</b>.</li>
          <li>Expéditeur inconnu : <b>rejeté</b>, sans réponse ; l'administrateur décide.</li>
        </ul>
      </div>
    </>
  );
}
