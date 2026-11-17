export function libelleDecision(d) {
  const t = { retenu: "Retenu", non_retenu: "Non retenu", a_valider: "À valider", bloque: "Bloqué", rejete: "Rejeté", inconnu: "Inconnu" };
  return t[d] || "En attente";
}
export function classeDecision(d) {
  if (d === "retenu") return "ok";
  if (d === "a_valider" || !d || d === "en_attente") return "attente";
  if (d === "non_retenu" || d === "bloque") return "alerte";
  return "";
}
export function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
