import { useState } from "react";

export function usePDVDescontoItens({ vendaAtual, setVendaAtual }) {
  const [mostrarModalDescontoItem, setMostrarModalDescontoItem] =
    useState(false);
  const [itemEditando, setItemEditando] = useState(null);

  const recalcularTotais = (itens) => {
    const subtotal = itens.reduce((sum, item) => sum + item.subtotal, 0);
    const descontoItens = itens.reduce(
      (sum, item) => sum + (item.desconto_valor || 0),
      0,
    );
    const totalBruto = subtotal + descontoItens;
    const descontoPercentual =
      totalBruto > 0 ? (descontoItens / totalBruto) * 100 : 0;
    const taxaEntrega = vendaAtual.tem_entrega
      ? vendaAtual.entrega?.taxa_entrega_total || 0
      : 0;
    const total = subtotal + taxaEntrega;

    setVendaAtual((prev) => ({
      ...prev,
      itens,
      subtotal,
      desconto_valor: descontoItens,
      desconto_percentual: descontoPercentual,
      total,
    }));
  };

  const abrirModalDescontoItem = (item) => {
    setItemEditando({
      ...item,
      preco: item.preco_unitario,
      descontoValor: item.desconto_valor || 0,
      descontoPercentual: item.desconto_percentual || 0,
      tipoDesconto: "valor",
    });
    setMostrarModalDescontoItem(true);
  };

  const salvarDescontoItem = () => {
    const itensAtualizados = vendaAtual.itens.map((item) => {
      if (item.produto_id === itemEditando.produto_id) {
        const precoUnitario = itemEditando.preco;
        const quantidade = item.quantidade;
        const subtotalSemDesconto = precoUnitario * quantidade;
        let descontoValor = 0;
        let descontoPercentual = 0;

        if (itemEditando.tipoDesconto === "valor") {
          descontoValor = parseFloat(itemEditando.descontoValor) || 0;
          descontoPercentual =
            subtotalSemDesconto > 0
              ? (descontoValor / subtotalSemDesconto) * 100
              : 0;
        } else {
          descontoPercentual = parseFloat(itemEditando.descontoPercentual) || 0;
          descontoValor = (subtotalSemDesconto * descontoPercentual) / 100;
        }

        const precoComDesconto = precoUnitario - descontoValor / quantidade;
        const subtotal = subtotalSemDesconto - descontoValor;

        return {
          ...item,
          desconto_valor: descontoValor,
          desconto_percentual: descontoPercentual,
          tipo_desconto_aplicado: itemEditando.tipoDesconto,
          preco_com_desconto: precoComDesconto,
          subtotal,
        };
      }
      return item;
    });

    recalcularTotais(itensAtualizados);
    setMostrarModalDescontoItem(false);
    setItemEditando(null);
  };

  const removerItemEditando = () => {
    if (!itemEditando) return;
    const novosItens = vendaAtual.itens.filter(
      (item) => item.produto_id !== itemEditando.produto_id,
    );
    recalcularTotais(novosItens);
    setMostrarModalDescontoItem(false);
    setItemEditando(null);
  };

  return {
    mostrarModalDescontoItem,
    setMostrarModalDescontoItem,
    itemEditando,
    setItemEditando,
    recalcularTotais,
    abrirModalDescontoItem,
    salvarDescontoItem,
    removerItemEditando,
  };
}
