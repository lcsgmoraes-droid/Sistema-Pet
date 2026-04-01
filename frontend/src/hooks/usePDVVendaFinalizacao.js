import { useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { buscarClientePorId } from "../api/clientes";
import { buscarVenda } from "../api/vendas";
import { debugLog } from "../utils/debug";

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

function montarMensagemErroExclusao(errorData) {
  if (errorData && typeof errorData === "object") {
    let mensagem = `âŒ ${errorData.erro || "Erro ao excluir venda"}\n\n`;
    mensagem += `${errorData.mensagem || ""}\n\n`;

    if (errorData.solucao) {
      mensagem += `ðŸ’¡ SoluÃ§Ã£o:\n${errorData.solucao}\n\n`;
    }

    if (errorData.passos && Array.isArray(errorData.passos)) {
      mensagem += "ðŸ“‹ Passos para resolver:\n";
      errorData.passos.forEach((passo) => {
        mensagem += `${passo}\n`;
      });
    }

    if (errorData.rota_id) {
      mensagem += `\nðŸšš Rota ID: ${errorData.rota_id}`;
      if (errorData.rota_status) {
        mensagem += ` (${errorData.rota_status})`;
      }
    }

    return mensagem;
  }

  if (typeof errorData === "string") {
    return errorData;
  }

  return "Erro ao excluir venda. Verifique se nÃ£o hÃ¡ vÃ­nculos pendentes.";
}

function montarVendaReaberta(vendaAtualizada, clienteCompleto) {
  return {
    id: vendaAtualizada.id,
    numero_venda: vendaAtualizada.numero_venda,
    data_venda: vendaAtualizada.data_venda,
    cliente: clienteCompleto,
    pet: null,
    itens: vendaAtualizada.itens || [],
    subtotal: parseFloat(vendaAtualizada.subtotal || vendaAtualizada.total),
    desconto_valor: parseFloat(vendaAtualizada.desconto_valor || 0),
    desconto_percentual: parseFloat(vendaAtualizada.desconto_percentual || 0),
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
  };
}

export function usePDVVendaFinalizacao({
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
          `âœ… Status restaurado para: ${statusOriginalVenda} (alteraÃ§Ãµes descartadas)`,
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
      "Deseja realmente excluir esta venda?\n\nEsta aÃ§Ã£o nÃ£o pode ser desfeita e o estoque serÃ¡ devolvido.",
    );

    if (!confirmar) return;

    try {
      setLoading(true);
      await api.delete(`/vendas/${vendaAtual.id}`);
      limparVenda();
      carregarVendasRecentes();
      alert("Venda excluÃ­da com sucesso!");
    } catch (error) {
      console.error("Erro ao excluir venda:", error);
      alert(montarMensagemErroExclusao(error.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  const mudarStatusParaAberta = async () => {
    if (!vendaAtual.id) return;

    const confirmar = window.confirm(
      'Deseja reabrir esta venda?\n\nOs pagamentos serÃ£o mantidos e o status mudarÃ¡ para "aberta".',
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

      setVendaAtual(montarVendaReaberta(vendaAtualizada, clienteCompleto));
      setModoVisualizacao(false);

      alert(
        "Venda reaberta com sucesso! Agora vocÃª pode editÃ¡-la.\n\nATENÃ‡ÃƒO: Se vocÃª nÃ£o fizer alteraÃ§Ãµes e sair, a venda voltarÃ¡ ao status anterior.",
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
        debugLog("âœ… Venda recarregada:", vendaAtualizada);
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
    habilitarEdicao,
    cancelarEdicao,
    excluirVenda,
    mudarStatusParaAberta,
    emitirNotaVendaFinalizada,
    handleConfirmarPagamento,
    handleVendaAtualizadaAposPagamento,
  };
}
