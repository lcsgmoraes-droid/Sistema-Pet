import { useState } from "react";

export function usePDVDescontoTotal({ vendaAtual, recalcularTotais, prepararDescontos }) {
  const [mostrarModalDescontoTotal, setMostrarModalDescontoTotal] = useState(false);
  const [tipoDescontoTotal, setTipoDescontoTotal] = useState("valor");
  const [valorDescontoTotal, setValorDescontoTotal] = useState(0);

  const abrirModalDescontoTotal = async () => {
    const preparada = await prepararDescontos();
    if (!preparada) return;
    if (preparada.desconto_venda_valor > 0) {
      setTipoDescontoTotal("valor");
      setValorDescontoTotal(preparada.desconto_venda_valor);
    } else {
      setTipoDescontoTotal("valor");
      setValorDescontoTotal(0);
    }
    setMostrarModalDescontoTotal(true);
  };

  const aplicarDescontoTotal = (tipoDesconto, valor, extras = {}) => {
    const itens = vendaAtual.itens;
    if (itens.length === 0) return;

    const totalBruto = Math.max(
      0,
      itens.reduce((sum, item) => sum + Number(item.subtotal || 0), 0) -
        Number(vendaAtual.cupom_discount_applied || 0),
    );

    let descontoTotal;
    if (tipoDesconto === "valor") {
      descontoTotal = Math.min(parseFloat(valor) || 0, totalBruto);
    } else {
      const pct = Math.min(parseFloat(valor) || 0, 100);
      descontoTotal = (totalBruto * pct) / 100;
    }

    recalcularTotais(itens, { desconto_venda_valor: Math.max(0, descontoTotal), ...extras });
    setMostrarModalDescontoTotal(false);
  };

  const removerDescontoTotal = async (extras = {}) => {
    const preparada = await prepararDescontos();
    if (!preparada) return;
    recalcularTotais(preparada.itens, { ...preparada, desconto_venda_valor: 0, ...extras });
  };

  return {
    mostrarModalDescontoTotal,
    setMostrarModalDescontoTotal,
    tipoDescontoTotal,
    setTipoDescontoTotal,
    valorDescontoTotal,
    setValorDescontoTotal,
    abrirModalDescontoTotal,
    aplicarDescontoTotal,
    removerDescontoTotal,
  };
}
