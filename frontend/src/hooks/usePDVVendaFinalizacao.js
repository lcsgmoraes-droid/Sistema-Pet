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
    let mensagem = `\u274c ${errorData.erro || "Erro ao excluir venda"}\n\n`;
    mensagem += `${errorData.mensagem || ""}\n\n`;

    if (errorData.solucao) {
      mensagem += `\ud83d\udca1 Solu\u00e7\u00e3o:\n${errorData.solucao}\n\n`;
    }

    if (errorData.passos && Array.isArray(errorData.passos)) {
      mensagem += "\ud83d\udccb Passos para resolver:\n";
      errorData.passos.forEach((passo) => {
        mensagem += `${passo}\n`;
      });
    }

    if (errorData.rota_id) {
      mensagem += `\n\ud83d\ude9a Rota ID: ${errorData.rota_id}`;
      if (errorData.rota_status) {
        mensagem += ` (${errorData.rota_status})`;
      }
    }

    return mensagem;
  }

  if (typeof errorData === "string") {
    return errorData;
  }

  return "Erro ao excluir venda. Verifique se n\u00e3o h\u00e1 v\u00ednculos pendentes.";
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
          `\u2705 Status restaurado para: ${statusOriginalVenda} (altera\u00e7\u00f5es descartadas)`,
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
      "Deseja realmente excluir esta venda?\n\nEsta a\u00e7\u00e3o n\u00e3o pode ser desfeita e o estoque ser\u00e1 devolvido.",
    );

    if (!confirmar) return;

    try {
      setLoading(true);
      await api.delete(`/vendas/${vendaAtual.id}`);
      limparVenda();
      carregarVendasRecentes();
      alert("Venda exclu\u00edda com sucesso!");
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
      'Deseja reabrir esta venda?\n\nOs pagamentos ser\u00e3o mantidos e o status mudar\u00e1 para "aberta".',
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
        "Venda reaberta com sucesso! Agora voc\u00ea pode edit\u00e1-la.\n\nATEN\u00c7\u00c3O: Se voc\u00ea n\u00e3o fizer altera\u00e7\u00f5es e sair, a venda voltar\u00e1 ao status anterior.",
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
        debugLog("\u2705 Venda recarregada:", vendaAtualizada);
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
