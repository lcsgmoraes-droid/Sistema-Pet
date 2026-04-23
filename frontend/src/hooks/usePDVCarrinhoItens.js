import { useState } from "react";
import { debugLog } from "../utils/debug";

function recalcularSubtotalItem(item, novaQuantidade) {
  const subtotalSemDesconto = novaQuantidade * item.preco_unitario;
  let novoDescontoValor = item.desconto_valor || 0;

  if (
    item.tipo_desconto_aplicado === "percentual" &&
    item.desconto_percentual > 0
  ) {
    novoDescontoValor = (subtotalSemDesconto * item.desconto_percentual) / 100;
  }

  return {
    ...item,
    quantidade: novaQuantidade,
    desconto_valor: novoDescontoValor,
    subtotal: subtotalSemDesconto - novoDescontoValor,
  };
}

export function usePDVCarrinhoItens({
  vendaAtual,
  setVendaAtual,
  temCaixaAberto,
  recalcularTotais,
}) {
  const [copiadoCodigoItem, setCopiadoCodigoItem] = useState("");
  const [itensKitExpandidos, setItensKitExpandidos] = useState({});

  const adicionarProdutoAoCarrinho = (produto) => {
    if (!temCaixaAberto) {
      alert(
        "\u274c N\u00e3o \u00e9 poss\u00edvel adicionar produtos sem caixa aberto. Abra um caixa primeiro.",
      );
      return false;
    }

    debugLog("\ud83d\uded2 Produto sendo adicionado:", {
      nome: produto.nome,
      categoria_id: produto.categoria_id,
      categoria_nome: produto.categoria_nome,
      peso_embalagem: produto.peso_embalagem,
      classificacao_racao: produto.classificacao_racao,
    });

    const itemExistente = vendaAtual.itens.find(
      (item) => item.produto_id === produto.id,
    );

    let novosItens;
    if (itemExistente) {
      novosItens = vendaAtual.itens.map((item) =>
        item.produto_id === produto.id
          ? {
              ...item,
              quantidade: item.quantidade + 1,
              subtotal: (item.quantidade + 1) * item.preco_unitario,
            }
          : item,
      );
    } else {
      novosItens = [
        ...vendaAtual.itens,
        {
          tipo: "produto",
          produto_id: produto.id,
          produto_nome: produto.nome,
          produto_codigo: produto.codigo || null,
          produto_imagem_principal: produto.imagem_principal || null,
          quantidade: 1,
          preco_unitario: parseFloat(produto.preco_venda),
          desconto_item: 0,
          subtotal: parseFloat(produto.preco_venda),
          pet_id: vendaAtual.pet?.id || null,
          tipo_produto: produto.tipo_produto,
          tipo_kit: produto.tipo_kit,
          composicao_kit: produto.composicao_kit || [],
          categoria_id: produto.categoria_id,
          categoria_nome: produto.categoria_nome,
          peso_pacote_kg: produto.peso_liquido || produto.peso_bruto,
          peso_embalagem: produto.peso_embalagem,
          classificacao_racao: produto.classificacao_racao,
          estoque_atual: produto.estoque_atual,
          estoque_virtual: produto.estoque_virtual,
        },
      ];
    }

    recalcularTotais(novosItens);
    return true;
  };

  const alterarQuantidade = (index, delta) => {
    const novosItens = vendaAtual.itens.map((item, itemIndex) =>
      itemIndex === index
        ? recalcularSubtotalItem(item, Math.max(1, item.quantidade + delta))
        : item,
    );

    recalcularTotais(novosItens);
  };

  const atualizarQuantidadeItem = (index, novaQuantidade) => {
    const novosItens = vendaAtual.itens.map((item, itemIndex) =>
      itemIndex === index ? recalcularSubtotalItem(item, novaQuantidade) : item,
    );

    recalcularTotais(novosItens);
  };

  const atualizarPetDoItem = (index, petId) => {
    setVendaAtual((prev) => ({
      ...prev,
      itens: prev.itens.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              pet_id: petId,
            }
          : item,
      ),
    }));
  };

  const removerItem = (index) => {
    const novosItens = vendaAtual.itens.filter(
      (_, itemIndex) => itemIndex !== index,
    );
    recalcularTotais(novosItens);
  };

  const toggleKitExpansion = (index) => {
    setItensKitExpandidos((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const copiarCodigoProdutoCarrinho = (codigo, chaveItem) => {
    if (!codigo) return;
    navigator.clipboard.writeText(String(codigo));
    setCopiadoCodigoItem(chaveItem);
    setTimeout(() => setCopiadoCodigoItem(""), 2000);
  };

  return {
    copiadoCodigoItem,
    itensKitExpandidos,
    adicionarProdutoAoCarrinho,
    alterarQuantidade,
    atualizarPetDoItem,
    atualizarQuantidadeItem,
    copiarCodigoProdutoCarrinho,
    removerItem,
    toggleKitExpansion,
  };
}
