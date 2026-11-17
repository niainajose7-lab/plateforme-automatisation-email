def maj(chemin, ancien, nouveau):
    t = open(chemin, encoding="utf-8-sig").read()
    if nouveau in t:
        print("deja fait :", chemin)
        return
    assert t.count(ancien) == 1, "introuvable : " + ancien[:40]
    open(chemin, "w", encoding="utf-8").write(t.replace(ancien, nouveau))
    print("OK :", chemin)

A = "backend/automatisation.py"
maj(A, '        statut, details = "en_attente_validation", None',
    '        incertain = incertain or any((a.configuration or {}).get("validation") for a in db.query(Action).filter(Action.regle_id == correspondance.id).all())\n        statut, details = "en_attente_validation", None')
R = "backend/regles.py"
maj(R, "    transfert_vers: Optional[str] = None  # une ou plusieurs adresses separees par , ou ;",
    "    transfert_vers: Optional[str] = None  # une ou plusieurs adresses separees par , ou ;\n    validation: bool = False")
maj(R, '                    "destinataires": adresses,',
    '                    "destinataires": adresses,\n                    "validation": payload.validation,')
maj(R, '            "transfert_vers": destinataire_de(db, r.id),',
    '            "transfert_vers": destinataire_de(db, r.id),\n            "validation": any((a.configuration or {}).get("validation") for a in db.query(Action).filter(Action.regle_id == r.id).all()),')

R = "frontend/src/Regles.jsx"
maj(R, '  const [transfert, setTransfert] = useState("");',
    '  const [transfert, setTransfert] = useState("");\n  const [validation, setValidation] = useState(false);')
maj(R, '          transfert_vers: transfert.trim() || null,',
    '          transfert_vers: transfert.trim() || null,\n          validation,')
maj(R, '      setTransfert("");',
    '      setTransfert("");\n      setValidation(false);')
maj(R, '            {info && <p className="succes">{info}</p>}',
    '            <label>\n              <input type="checkbox" checked={validation} onChange={(e) => setValidation(e.target.checked)} />\n              {" "}Demander ma validation avant d\'agir\n            </label>\n\n            {info && <p className="succes">{info}</p>}')
maj(R, '? "Alors transferer a " + r.transfert_vers',
    '? "Alors transferer a " + r.transfert_vers + (r.validation ? " (apres votre validation)" : "")')
T = "frontend/src/Tableau.jsx"
maj(T, '{LIBELLES_DECISION[e.decision] || "En attente"}',
    '{e.decision === "retenu" && e.execution && e.execution.statut === "ignore" ? "Ignore" : LIBELLES_DECISION[e.decision] || "En attente"}')
