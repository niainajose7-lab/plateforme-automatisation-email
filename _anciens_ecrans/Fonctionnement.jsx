export default function Fonctionnement() {
  const etapes = [
    ["1. Lecture", "Toutes les minutes, la plateforme lit les nouveaux emails de ta boîte Gmail et les enregistre."],
    ["2. Pièces jointes", "Si l'email contient une image ou un PDF, elle en lit le texte (OpenCV et OCR) et en extrait le numéro, le montant et les dates."],
    ["3. Classement", "Elle devine la catégorie de l'email : facture, réclamation, demande ou autre (score à poids ou réseau PyTorch)."],
    ["4. Règles", "Elle compare l'email à tes règles actives : « si … alors … »."],
    ["5. Décision et action", "Si une règle correspond, l'email est retenu et l'action s'exécute (transfert). Sinon, il est non retenu."],
  ];
  return (
    <>
      <section className="bloc">
        <h2>Comment la plateforme fonctionne</h2>
        <p className="aide">Tout se passe automatiquement, sans que tu aies à intervenir.</p>
        <div className="liste">
          {etapes.map(([titre, texte]) => (
            <div className="regle" key={titre}>
              <div>
                <strong>{titre}</strong>
                <div className="aide">{texte}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="bloc">
        <h2>Les catégories</h2>
        <table>
          <tbody>
            <tr><td><strong>facture</strong></td><td>un paiement ou un montant à régler</td></tr>
            <tr><td><strong>reclamation</strong></td><td>une plainte, un mécontentement</td></tr>
            <tr><td><strong>demande</strong></td><td>une question ou une demande d'information, de devis</td></tr>
            <tr><td><strong>autre</strong></td><td>tout le reste : notifications, newsletters, publicités</td></tr>
          </tbody>
        </table>
      </section>

      <section className="bloc">
        <h2>Les décisions</h2>
        <table>
          <tbody>
            <tr><td><span className="badge retenu">Retenu</span></td><td>une règle active correspond : l'action est exécutée</td></tr>
            <tr><td><span className="badge non_retenu">Non retenu</span></td><td>aucune règle ne correspond : rien n'est fait</td></tr>
            <tr><td><span className="badge a_valider">À valider</span></td><td>une règle correspond, mais la confiance est trop faible : attente de ton accord</td></tr>
            <tr><td><span className="badge">En attente</span></td><td>email pas encore traité</td></tr>
          </tbody>
        </table>
        <p className="aide">
          La confiance indique à quel point le programme est sûr de la catégorie. La décision,
          elle, ne dépend que de tes règles.
        </p>
      </section>

      <section className="bloc">
        <h2>Une règle</h2>
        <p className="aide">
          Une règle est une consigne : <strong>Si</strong> l'email correspond à une condition
          (par exemple : la catégorie est « facture »), <strong>alors</strong> la plateforme le
          retient et le transfère à l'adresse choisie.
        </p>
      </section>
    </>
  );
}
