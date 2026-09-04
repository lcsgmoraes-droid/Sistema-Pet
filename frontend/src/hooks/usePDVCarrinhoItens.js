import { useState } from "react";
import { debugLog } from "../utils/debug";
import {
  colocarItemProdutoNoTopo,
  obterPrecoVendaPDV,
  recalcularSubtotalItem,
} from "../utils/pdvCarrinhoItensUtils";
import { sugerirProtocoloRecorrencia } from "../utils/pdvProtocolosRecorrencia";

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

    const itemExistente = vendaAtual.itens.find((item) => item.produto_id === produto.id);

    const precoUnitario = obterPrecoVendaPDV(produto);
    const promocaoAtiva = Boolean(produto.promocao_pdv_ativa);

    let novosItens;
    if (itemExistente) {
      novosItens = colocarItemProdutoNoTopo(
        vendaAtual.itens,
        recalcularSubtotalItem(itemExistente, itemExistente.quantidade + 1),
      );
    } else {
      novosItens = colocarItemProdutoNoTopo(vendaAtual.itens, {
        tipo:
          produto.controlar_estoque === false || produto.tipo === "servico" ? "servico" : "produto",
        produto_id: produto.id,
        produto_nome: produto.nome,
        produto_codigo: produto.codigo || null,
        produto_imagem_principal: produto.imagem_principal || null,
        produto_imagem_thumbnail: produto.imagem_principal_thumbnail || null,
        quantidade: 1,
        preco_unitario: precoUnitario,
        preco_venda_original: produto.preco_venda_original ?? produto.preco_venda ?? precoUnitario,
        em_promocao: promocaoAtiva,
        promocao_origem: produto.promocao_origem_pdv || (promocaoAtiva ? "Promocao ERP" : null),
        desconto_promocional_unitario: produto.desconto_promocional_pdv || 0,
        desconto_item: 0,
        subtotal: precoUnitario,
        pet_id: vendaAtual.pet?.id || null,
        protocolo_recorrencia_id: sugerirProtocoloRecorrencia(
          produto.protocolos_recorrencia || [],
          vendaAtual.pet,
        ),
        ignorar_recorrencia: false,
        protocolos_recorrencia: produto.protocolos_recorrencia || [],
        tipo_produto: produto.tipo_produto,
        tipo_kit: produto.tipo_kit,
        composicao_kit: produto.composicao_kit || [],
        categoria_id: produto.categoria_id,
        categoria_nome: produto.categoria_nome,
        eh_racao: produto.eh_racao,
        peso_pacote_kg: produto.peso_liquido || produto.peso_bruto,
        peso_embalagem: produto.peso_embalagem,
        classificacao_racao: produto.classificacao_racao,
        estoque_atual: produto.estoque_atual,
        estoque_virtual: produto.estoque_virtual,
        controlar_estoque: produto.controlar_estoque !== false && produto.tipo !== "servico",
        estoque_compartilhado: Boolean(produto.estoque_compartilhado),
        estoque_compartilhado_id: produto.estoque_compartilhado_id || null,
        estoque_origem_empresa_id: produto.estoque_origem_empresa_id || null,
        estoque_origem_nome: produto.estoque_origem_nome || null,
      });
    }

    recalcularTotais(novosItens);
    return true;
  };

  const alterarQuantidade = (index, delta) => {
    const novosItens = vendaAtual.itens.map((item, itemIndex) =>
      itemIndex === index ? recalcularSubtotalItem(item, item.quantidade + delta) : item,
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
              protocolo_recorrencia_id: sugerirProtocoloRecorrencia(
                item.protocolos_recorrencia || item.produto?.protocolos_recorrencia || [],
                prev.cliente?.pets?.find((pet) => Number(pet.id) === Number(petId)) || null,
              ),
              ignorar_recorrencia: false,
            }
          : item,
      ),
    }));
  };

  const atualizarProtocoloDoItem = (index, protocoloId) => {
    setVendaAtual((prev) => ({
      ...prev,
      itens: prev.itens.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              protocolo_recorrencia_id: protocoloId,
              ignorar_recorrencia: protocoloId === null,
            }
          : item,
      ),
    }));
  };

  const removerItem = (index) => {
    const novosItens = vendaAtual.itens.filter((_, itemIndex) => itemIndex !== index);
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
    atualizarProtocoloDoItem,
    atualizarQuantidadeItem,
    copiarCodigoProdutoCarrinho,
    removerItem,
    toggleKitExpansion,
  };
}
