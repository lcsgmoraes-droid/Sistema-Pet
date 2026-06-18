import { useState } from "react";
import { recalcularItemComPrecoEDesconto } from "../utils/pdvDescontoItensUtils";

export function usePDVDescontoItens({ vendaAtual, setVendaAtual }) {
  const [mostrarModalDescontoItem, setMostrarModalDescontoItem] = useState(false);
  const [itemEditando, setItemEditando] = useState(null);

  const recalcularTotais = (itens, extras = {}) => {
    const subtotal = itens.reduce((sum, item) => sum + item.subtotal, 0);
    const descontoItens = itens.reduce((sum, item) => sum + (item.desconto_valor || 0), 0);
    const totalBruto = subtotal + descontoItens;
    const descontoPercentual = totalBruto > 0 ? (descontoItens / totalBruto) * 100 : 0;
    const taxaEntrega = vendaAtual.tem_entrega ? vendaAtual.entrega?.taxa_entrega_total || 0 : 0;
    const total = subtotal + taxaEntrega;

    setVendaAtual((prev) => ({
      ...prev,
      itens,
      subtotal,
      desconto_valor: descontoItens,
      desconto_percentual: descontoPercentual,
      total,
      ...extras,
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
        return recalcularItemComPrecoEDesconto(item, itemEditando);
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
