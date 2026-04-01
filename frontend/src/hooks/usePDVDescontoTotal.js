import { useState } from "react";

export function usePDVDescontoTotal({ vendaAtual, recalcularTotais }) {
  const [mostrarModalDescontoTotal, setMostrarModalDescontoTotal] =
    useState(false);
  const [tipoDescontoTotal, setTipoDescontoTotal] = useState("valor");
  const [valorDescontoTotal, setValorDescontoTotal] = useState(0);

  const abrirModalDescontoTotal = () => {
    if (vendaAtual.desconto_valor > 0) {
      setTipoDescontoTotal("valor");
      setValorDescontoTotal(vendaAtual.desconto_valor);
    } else {
      setTipoDescontoTotal("valor");
      setValorDescontoTotal(0);
    }
    setMostrarModalDescontoTotal(true);
  };

  const aplicarDescontoTotal = (tipoDesconto, valor) => {
    const itens = vendaAtual.itens;
    if (itens.length === 0) return;

    const subtotaisBrutos = itens.map(
      (item) => (item.preco_unitario || item.preco_venda) * item.quantidade,
    );
    const totalBruto = subtotaisBrutos.reduce((sum, v) => sum + v, 0);

    let descontoTotal = 0;
    if (tipoDesconto === "valor") {
      descontoTotal = Math.min(parseFloat(valor) || 0, totalBruto);
    } else {
      const pct = Math.min(parseFloat(valor) || 0, 100);
      descontoTotal = (totalBruto * pct) / 100;
    }

    let descontoAlocado = 0;
    const itensAtualizados = itens.map((item, idx) => {
      const subtotalBrutoItem = subtotaisBrutos[idx];
      let descontoItem;

      if (idx === itens.length - 1) {
        descontoItem = parseFloat((descontoTotal - descontoAlocado).toFixed(2));
      } else {
        const proporcao = totalBruto > 0 ? subtotalBrutoItem / totalBruto : 0;
        descontoItem = parseFloat((descontoTotal * proporcao).toFixed(2));
        descontoAlocado += descontoItem;
      }

      const descontoPercentual =
        subtotalBrutoItem > 0 ? (descontoItem / subtotalBrutoItem) * 100 : 0;
      const subtotal = subtotalBrutoItem - descontoItem;
      const precoComDesconto =
        item.quantidade > 0 ? subtotal / item.quantidade : 0;

      return {
        ...item,
        desconto_valor: descontoItem,
        desconto_percentual: descontoPercentual,
        tipo_desconto_aplicado: tipoDesconto,
        preco_com_desconto: precoComDesconto,
        subtotal,
      };
    });

    recalcularTotais(itensAtualizados);
    setMostrarModalDescontoTotal(false);
  };

  const removerDescontoTotal = () => {
    const itensAtualizados = vendaAtual.itens.map((item) => {
      const subtotalBruto =
        (item.preco_unitario || item.preco_venda) * item.quantidade;
      return {
        ...item,
        desconto_valor: 0,
        desconto_percentual: 0,
        tipo_desconto_aplicado: null,
        preco_com_desconto: item.preco_unitario || item.preco_venda,
        subtotal: subtotalBruto,
      };
    });
    recalcularTotais(itensAtualizados);
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
