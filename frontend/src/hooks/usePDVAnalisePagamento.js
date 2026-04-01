import { useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { buscarClientePorId } from "../api/clientes";
import { buscarVenda } from "../api/vendas";
import { debugLog } from "../utils/debug";

function montarItensAnalise(itens = []) {
  return itens.map((item) => ({
    produto_id: item.produto_id,
    quantidade: item.quantidade,
    preco_venda: item.preco_unitario || item.preco_venda,
    custo: item.custo,
  }));
}

async function carregarPagamentosDaVenda(vendaId) {
  try {
    const responsePagamentos = await api.get(`/vendas/${vendaId}/pagamentos`);
    return {
      pagamentos: responsePagamentos.data.pagamentos || [],
      totalPago: responsePagamentos.data.total_pago || 0,
    };
  } catch (error) {
    console.error("Erro ao buscar pagamentos:", error);
    return {
      pagamentos: [],
      totalPago: 0,
    };
  }
}

export function usePDVAnalisePagamento({
  vendaAtual,
  setVendaAtual,
  setLoading,
  modoVisualizacao,
  setModoVisualizacao,
  setMostrarModalPagamento,
  limparVenda,
  carregarVendaEspecifica,
  carregarVendasRecentes,
}) {
  const [statusOriginalVenda, setStatusOriginalVenda] = useState(null);
  const [mostrarAnaliseVenda, setMostrarAnaliseVenda] = useState(false);
  const [dadosAnalise, setDadosAnalise] = useState(null);
  const [carregandoAnalise, setCarregandoAnalise] = useState(false);

  const buscarAnaliseVenda = async () => {
    if (vendaAtual.itens.length === 0) {
      alert("Adicione pelo menos um produto para ver a análise");
      return;
    }

    setCarregandoAnalise(true);
    setMostrarAnaliseVenda(true);

    try {
      const response = await api.post("/formas-pagamento/analisar-venda", {
        items: montarItensAnalise(vendaAtual.itens),
        desconto: vendaAtual.desconto_valor || 0,
        taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
        forma_pagamento_id: vendaAtual.forma_pagamento_id || null,
        parcelas: vendaAtual.parcelas || 1,
        vendedor_id: vendaAtual.funcionario_id,
      });

      setDadosAnalise(response.data);
    } catch (error) {
      console.error("Erro ao buscar análise:", error);
      alert("Erro ao carregar análise da venda");
      setMostrarAnaliseVenda(false);
    } finally {
      setCarregandoAnalise(false);
    }
  };

  const analisarVenda = async (vendaId) => {
    setCarregandoAnalise(true);
    setMostrarAnaliseVenda(true);

    try {
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
      console.error("Erro ao buscar análise:", error);
      alert("Erro ao carregar análise da venda");
      setMostrarAnaliseVenda(false);
    } finally {
      setCarregandoAnalise(false);
    }
  };

  const analisarVendaComFormasPagamento = async (formasPagamento) => {
    debugLog("🔍 DEBUG formasPagamento recebidas:", formasPagamento);

    setCarregandoAnalise(true);
    setMostrarAnaliseVenda(true);

    try {
      debugLog("💰 Enviando análise com múltiplas formas:", formasPagamento);

      const response = await api.post("/formas-pagamento/analisar-venda", {
        items: montarItensAnalise(vendaAtual.itens),
        desconto: vendaAtual.desconto_valor || 0,
        taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
        formas_pagamento: formasPagamento,
        vendedor_id: vendaAtual.funcionario_id,
      });

      debugLog("✅ Resposta da análise:", response.data);
      setDadosAnalise(response.data);
    } catch (error) {
      console.error("Erro ao buscar análise:", error);
      alert("Erro ao carregar análise da venda");
      setMostrarAnaliseVenda(false);
    } finally {
      setCarregandoAnalise(false);
    }
  };

  const habilitarEdicao = () => {
    setModoVisualizacao(false);
  };

  const cancelarEdicao = async () => {
    if (!vendaAtual.id) {
      limparVenda();
      return;
    }

    if (statusOriginalVenda && vendaAtual.status !== statusOriginalVenda) {
      try {
        setLoading(true);
        await api.patch(`/vendas/${vendaAtual.id}/status`, {
          status: statusOriginalVenda,
        });

        debugLog(
          `✅ Status restaurado para: ${statusOriginalVenda} (alterações descartadas)`,
        );
      } catch (error) {
        console.error("Erro ao restaurar status:", error);
      } finally {
        setLoading(false);
      }
    }

    setStatusOriginalVenda(null);
    limparVenda();
  };

  const excluirVenda = async () => {
    if (!vendaAtual.id) return;

    const confirmar = window.confirm(
      "Deseja realmente excluir esta venda?\n\nEsta ação não pode ser desfeita e o estoque será devolvido.",
    );

    if (!confirmar) return;

    try {
      setLoading(true);
      await api.delete(`/vendas/${vendaAtual.id}`);
      limparVenda();
      carregarVendasRecentes();
      alert("Venda excluída com sucesso!");
    } catch (error) {
      console.error("Erro ao excluir venda:", error);

      const errorData = error.response?.data?.detail;

      if (errorData && typeof errorData === "object") {
        let mensagem = `❌ ${errorData.erro || "Erro ao excluir venda"}\n\n`;
        mensagem += `${errorData.mensagem || ""}\n\n`;

        if (errorData.solucao) {
          mensagem += `💡 Solução:\n${errorData.solucao}\n\n`;
        }

        if (errorData.passos && Array.isArray(errorData.passos)) {
          mensagem += `📋 Passos para resolver:\n`;
          errorData.passos.forEach((passo) => {
            mensagem += `${passo}\n`;
          });
        }

        if (errorData.rota_id) {
          mensagem += `\n🚚 Rota ID: ${errorData.rota_id}`;
          if (errorData.rota_status) {
            mensagem += ` (${errorData.rota_status})`;
          }
        }

        alert(mensagem);
      } else if (typeof errorData === "string") {
        alert(errorData);
      } else {
        alert("Erro ao excluir venda. Verifique se não há vínculos pendentes.");
      }
    } finally {
      setLoading(false);
    }
  };

  const mudarStatusParaAberta = async () => {
    if (!vendaAtual.id) return;

    const confirmar = window.confirm(
      'Deseja reabrir esta venda?\n\nOs pagamentos serão mantidos e o status mudará para "aberta".',
    );

    if (!confirmar) return;

    setStatusOriginalVenda(vendaAtual.status);

    try {
      setLoading(true);
      await api.post(`/vendas/${vendaAtual.id}/reabrir`);

      const vendaAtualizada = await buscarVenda(vendaAtual.id);

      let clienteCompleto = null;
      if (vendaAtualizada.cliente_id) {
        clienteCompleto = await buscarClientePorId(vendaAtualizada.cliente_id);
      }

      setVendaAtual({
        id: vendaAtualizada.id,
        numero_venda: vendaAtualizada.numero_venda,
        data_venda: vendaAtualizada.data_venda,
        cliente: clienteCompleto,
        pet: null,
        itens: vendaAtualizada.itens || [],
        subtotal: parseFloat(vendaAtualizada.subtotal || vendaAtualizada.total),
        desconto_valor: parseFloat(vendaAtualizada.desconto_valor || 0),
        desconto_percentual: parseFloat(
          vendaAtualizada.desconto_percentual || 0,
        ),
        total: parseFloat(vendaAtualizada.total),
        observacoes: vendaAtualizada.observacoes || "",
        status: "aberta",
        tem_entrega: vendaAtualizada.tem_entrega || false,
        entrega: {
          endereco_completo: vendaAtualizada.endereco_entrega || "",
          endereco_id: vendaAtualizada.endereco_id || null,
          taxa_entrega_total: parseFloat(
            parseFloat(vendaAtualizada.taxa_entrega || 0).toFixed(2),
          ),
          taxa_loja: parseFloat(
            parseFloat(vendaAtualizada.taxa_loja || 0).toFixed(2),
          ),
          taxa_entregador: parseFloat(
            parseFloat(vendaAtualizada.taxa_entregador || 0).toFixed(2),
          ),
          observacoes_entrega: vendaAtualizada.observacoes_entrega || "",
          distancia_km: vendaAtualizada.distancia_km || 0,
          valor_por_km: vendaAtualizada.valor_por_km || 0,
          loja_origem: vendaAtualizada.loja_origem || "",
          status_entrega: vendaAtualizada.status_entrega || "pendente",
        },
      });

      setModoVisualizacao(false);

      alert(
        "Venda reaberta com sucesso! Agora você pode editá-la.\n\nATENÇÃO: Se você não fizer alterações e sair, a venda voltará ao status anterior.",
      );
    } catch (error) {
      console.error("Erro ao reabrir venda:", error);
      alert(error.response?.data?.detail || "Erro ao reabrir venda");
    } finally {
      setLoading(false);
    }
  };

  const emitirNotaVendaFinalizada = async () => {
    if (!vendaAtual.id) return;

    let tipoNota = "nfce";
    if (vendaAtual.cliente?.cnpj) {
      const emitirNfe = window.confirm(
        "Cliente tem CNPJ.\n\nClique OK para emitir NF-e (Empresa)\nClique Cancelar para emitir NFC-e (Cupom).",
      );
      tipoNota = emitirNfe ? "nfe" : "nfce";
    }

    const confirmar = window.confirm(
      `Confirma emitir ${tipoNota === "nfe" ? "NF-e" : "NFC-e"} para esta venda finalizada?`,
    );
    if (!confirmar) return;

    try {
      setLoading(true);
      await api.post("/nfe/emitir", {
        venda_id: vendaAtual.id,
        tipo_nota: tipoNota,
      });

      await carregarVendaEspecifica(vendaAtual.id);
      toast.success(
        `${tipoNota === "nfe" ? "NF-e" : "NFC-e"} emitida com sucesso!`,
      );
    } catch (error) {
      console.error("Erro ao emitir nota da venda finalizada:", error);
      alert(error.response?.data?.detail || "Erro ao emitir nota fiscal");
    } finally {
      setLoading(false);
    }
  };

  const recarregarVendaAtualComPagamentos = async (vendaId) => {
    const vendaAtualizada = await buscarVenda(vendaId);
    const { pagamentos, totalPago } = await carregarPagamentosDaVenda(vendaId);

    setVendaAtual({
      ...vendaAtualizada,
      pagamentos,
      total_pago: totalPago,
    });

    return vendaAtualizada;
  };

  const handleConfirmarPagamento = async () => {
    setMostrarModalPagamento(false);

    if (modoVisualizacao && vendaAtual.id) {
      try {
        const vendaAtualizada = await recarregarVendaAtualComPagamentos(
          vendaAtual.id,
        );
        debugLog("✅ Venda recarregada:", vendaAtualizada);
      } catch (error) {
        console.error("Erro ao recarregar venda:", error);
      }
    } else {
      limparVenda();
    }

    carregarVendasRecentes();
  };

  const handleVendaAtualizadaAposPagamento = async () => {
    if (!vendaAtual.id) {
      return;
    }

    const vendaAtualizada = await recarregarVendaAtualComPagamentos(
      vendaAtual.id,
    );
    setModoVisualizacao(
      vendaAtualizada.status === "finalizada" ||
        vendaAtualizada.status === "baixa_parcial",
    );
    carregarVendasRecentes();
  };

  return {
    mostrarAnaliseVenda,
    setMostrarAnaliseVenda,
    dadosAnalise,
    carregandoAnalise,
    buscarAnaliseVenda,
    analisarVenda,
    analisarVendaComFormasPagamento,
    habilitarEdicao,
    cancelarEdicao,
    excluirVenda,
    mudarStatusParaAberta,
    emitirNotaVendaFinalizada,
    handleConfirmarPagamento,
    handleVendaAtualizadaAposPagamento,
  };
}
