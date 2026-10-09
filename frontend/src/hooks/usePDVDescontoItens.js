import { useState } from "react";
import { recalcularItemComPrecoEDesconto } from "../utils/pdvDescontoItensUtils";
import { obterDescontoItem, recalcularVendaComDescontos } from "../utils/pdvDescontosUtils";

export function usePDVDescontoItens({ vendaAtual, setVendaAtual }) {
  const [mostrarModalDescontoItem, setMostrarModalDescontoItem] = useState(false);
  const [itemEditando, setItemEditando] = useState(null);

  const recalcularTotais = (itens, extras = {}) => {
    setVendaAtual((prev) => recalcularVendaComDescontos(prev, itens, extras));
  };

  const abrirModalDescontoItem = (item, index) => {
    setItemEditando({
      ...item,
      indice_carrinho: index,
      preco: item.preco_unitario,
      descontoValor: obterDescontoItem(item),
      descontoPercentual: item.desconto_percentual || 0,
      tipoDesconto: "valor",
    });
    setMostrarModalDescontoItem(true);
  };

  const salvarDescontoItem = () => {
    const itensAtualizados = vendaAtual.itens.map((item, index) => {
      if (index === itemEditando.indice_carrinho) {
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
      (_item, index) => index !== itemEditando.indice_carrinho,
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
