import { normalizarNumero } from "./transferenciaParceiroUtils.js";

export function calcularDevolucaoParceiro(registro, quantidades = {}) {
  const disponiveis = registro.itens_devolucao || [];
  const itens = [];
  let totalCentavos = 0;
  for (const [produtoId, entrada] of Object.entries(quantidades)) {
    const quantidade = normalizarNumero(entrada);
    if (quantidade === 0) continue;
    const item = disponiveis.find((produto) => produto.produto_id === Number(produtoId));
    if (!item || !Number.isFinite(quantidade) || quantidade < 0) {
      return { itens: [], total: 0, erro: "Informe quantidades válidas para a devolução." };
    }
    const unidades = Math.round(quantidade * 1000);
    if (Math.abs(quantidade * 1000 - unidades) > 0.000001) {
      return { itens: [], total: 0, erro: "Use até 3 casas decimais nas quantidades." };
    }
    if (unidades > Math.round(item.quantidade_disponivel * 1000)) {
      return {
        itens: [],
        total: 0,
        erro: `A quantidade de ${item.produto_nome} ultrapassa o restante.`,
      };
    }
    const acumulado = Math.round(
      (Math.round(item.valor_total * 100) *
        (Math.round(item.quantidade_devolvida * 1000) + unidades)) /
        Math.round(item.quantidade * 1000),
    );
    const centavos = acumulado - Math.round(item.valor_devolvido * 100);
    if (centavos < 0) {
      return { itens: [], total: 0, erro: "Confira os valores das devoluções anteriores." };
    }
    totalCentavos += centavos;
    itens.push({ produto_id: Number(produtoId), quantidade, valor_total: centavos / 100 });
  }
  const total = totalCentavos / 100;
  const erro =
    totalCentavos > Math.round(Number(registro.saldo_aberto || 0) * 100)
      ? "O valor dos produtos devolvidos ultrapassa o saldo da transferência."
      : null;
  return { itens, total, erro };
}
