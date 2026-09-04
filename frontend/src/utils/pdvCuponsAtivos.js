export function filtrarCuponsValidosPdv(cupons = [], agora = new Date()) {
  const instanteAtual = agora instanceof Date ? agora.getTime() : new Date(agora).getTime();

  return (Array.isArray(cupons) ? cupons : []).filter((cupom) => {
    const status = String(cupom?.status || "active").toLowerCase();
    if (status !== "active" && status !== "ativo") return false;
    if (!cupom?.valid_until) return true;

    const validade = new Date(cupom.valid_until).getTime();
    if (Number.isNaN(validade) || Number.isNaN(instanteAtual)) return false;
    return validade >= instanteAtual;
  });
}
