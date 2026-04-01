import { useState } from "react";
import api from "../api";
import { debugLog } from "../utils/debug";

function montarItensAnalise(itens = []) {
  return itens.map((item) => ({
    produto_id: item.produto_id,
    quantidade: item.quantidade,
    preco_venda: item.preco_unitario || item.preco_venda,
    custo: item.custo,
  }));
}

export function usePDVVendaAnalise(vendaAtual) {
  const [mostrarAnaliseVenda, setMostrarAnaliseVenda] = useState(false);
  const [dadosAnalise, setDadosAnalise] = useState(null);
  const [carregandoAnalise, setCarregandoAnalise] = useState(false);

  const executarAnalise = async (payload) => {
    setCarregandoAnalise(true);
    setMostrarAnaliseVenda(true);

    try {
      const response = await api.post("/formas-pagamento/analisar-venda", payload);
      setDadosAnalise(response.data);
    } catch (error) {
      console.error("Erro ao buscar anÃ¡lise:", error);
      alert("Erro ao carregar anÃ¡lise da venda");
      setMostrarAnaliseVenda(false);
    } finally {
      setCarregandoAnalise(false);
    }
  };

  const buscarAnaliseVenda = async () => {
    if (vendaAtual.itens.length === 0) {
      alert("Adicione pelo menos um produto para ver a anÃ¡lise");
      return;
    }

    await executarAnalise({
      items: montarItensAnalise(vendaAtual.itens),
      desconto: vendaAtual.desconto_valor || 0,
      taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
      forma_pagamento_id: vendaAtual.forma_pagamento_id || null,
      parcelas: vendaAtual.parcelas || 1,
      vendedor_id: vendaAtual.funcionario_id,
    });
  };

  const analisarVenda = async (vendaId) => {
    try {
      setCarregandoAnalise(true);
      setMostrarAnaliseVenda(true);

      const vendaResponse = await api.get(`/vendas/${vendaId}`);
      const venda = vendaResponse.data;

      const response = await api.post("/formas-pagamento/analisar-venda", {
        items: montarItensAnalise(venda.itens),
        desconto: venda.desconto_valor || 0,
        taxa_entrega: venda.entrega?.taxa_entrega_total || 0,
        forma_pagamento_id: venda.forma_pagamento_id || null,
        parcelas: venda.parcelas || 1,
        vendedor_id: venda.vendedor_id || null,
      });

      setDadosAnalise(response.data);
    } catch (error) {
      console.error("Erro ao buscar anÃ¡lise:", error);
      alert("Erro ao carregar anÃ¡lise da venda");
      setMostrarAnaliseVenda(false);
    } finally {
      setCarregandoAnalise(false);
    }
  };

  const analisarVendaComFormasPagamento = async (formasPagamento) => {
    debugLog("ðŸ” DEBUG formasPagamento recebidas:", formasPagamento);
    debugLog("ðŸ’° Enviando anÃ¡lise com mÃºltiplas formas:", formasPagamento);

    await executarAnalise({
      items: montarItensAnalise(vendaAtual.itens),
      desconto: vendaAtual.desconto_valor || 0,
      taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
      formas_pagamento: formasPagamento,
      vendedor_id: vendaAtual.funcionario_id,
    });
  };

  return {
    mostrarAnaliseVenda,
    setMostrarAnaliseVenda,
    dadosAnalise,
    carregandoAnalise,
    buscarAnaliseVenda,
    analisarVenda,
    analisarVendaComFormasPagamento,
  };
}
