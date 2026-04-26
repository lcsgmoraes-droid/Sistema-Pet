export function formatData(iso) {
  if (!iso) return "-";
  return new Date(`${iso}T12:00:00`).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function badgeStatus(status) {
  switch (status) {
    case "recebido":
      return { label: "Recebido", cls: "bg-green-100 text-green-700" };
    case "pendente":
      return { label: "Pendente", cls: "bg-yellow-100 text-yellow-700" };
    case "vencido":
      return { label: "Vencido", cls: "bg-red-100 text-red-700" };
    default:
      return { label: status, cls: "bg-gray-100 text-gray-600" };
  }
}

export function badgeTipo(tipo) {
  if (tipo === "repasse_empresa") {
    return { label: "Repasse empresa", cls: "bg-sky-100 text-sky-700" };
  }
  return { label: "Liquido veterinario", cls: "bg-violet-100 text-violet-700" };
}

export function periodoInicial() {
  const hoje = new Date().toISOString().slice(0, 10);
  return {
    hoje,
    primeiroDiaMes: `${hoje.slice(0, 8)}01`,
  };
}

export function calcularTotaisRepasse(itens) {
  const totalFiltrado = itens.reduce((soma, item) => soma + (item.valor || 0), 0);
  const totalRecebidoFiltrado = itens
    .filter((item) => item.status === "recebido")
    .reduce((soma, item) => soma + (item.valor || 0), 0);
  return {
    totalFiltrado,
    totalRecebidoFiltrado,
    totalPendenteFiltrado: totalFiltrado - totalRecebidoFiltrado,
    qtdRecebidos: itens.filter((item) => item.status === "recebido").length,
    qtdPendentes: itens.filter((item) => item.status !== "recebido").length,
  };
}
