import api from "../api";
import { criarVenda } from "../api/vendas";
import { montarPayloadVenda } from "../utils/pdvVendaPayload";
import { debugLog } from "../utils/debug";

function calcularStatusPorPagamento(totalPago, totalVenda) {
  if (totalPago >= totalVenda - 0.01) {
    return "finalizada";
  }

  if (totalPago > 0) {
    return "baixa_parcial";
  }

  return "aberta";
}

async function buscarTotalPago(vendaId) {
  try {
    const responsePagamentos = await api.get(`/vendas/${vendaId}/pagamentos`);
    return responsePagamentos.data.total_pago || 0;
  } catch (error) {
    console.error("Erro ao buscar pagamentos:", error);
    return 0;
  }
}

export function usePDVSalvarVenda({
  vendaAtual,
  loading,
  setLoading,
  temCaixaAberto,
  entregadorSelecionado,
  vendaComissionada,
  funcionarioComissao,
  limparVenda,
  carregarVendasRecentes,
}) {
  const salvarVenda = async () => {
    if (vendaAtual.itens.length === 0) {
      alert("Adicione pelo menos um produto ou serviço");
      return;
    }

    if (!temCaixaAberto) {
      alert(
        "❌ Não é possível salvar venda sem caixa aberto. Abra um caixa primeiro.",
      );
      return;
    }

    if (loading) return;

    setLoading(true);
    try {
      const payloadVenda = montarPayloadVenda(
        vendaAtual,
        entregadorSelecionado,
      );

      if (vendaAtual.id) {
        await api.put(`/vendas/${vendaAtual.id}`, payloadVenda);

        debugLog("🚨 DEBUG - Payload sendo enviado:", {
          payload: payloadVenda,
          vendaAtual_completo: vendaAtual,
        });

        const totalPago = await buscarTotalPago(vendaAtual.id);
        const novoStatus = calcularStatusPorPagamento(totalPago, vendaAtual.total);

        if (vendaAtual.status !== novoStatus) {
          await api.patch(`/vendas/${vendaAtual.id}/status`, {
            status: novoStatus,
          });
          debugLog(
            `✅ Status atualizado: ${vendaAtual.status} → ${novoStatus}`,
          );
        }

        alert("Venda atualizada com sucesso!");
        limparVenda();
      } else {
        debugLog("🚀 CRIANDO VENDA - payload consolidado");
        debugLog("Desconto valor:", payloadVenda.desconto_valor);
        debugLog("Desconto percentual:", payloadVenda.desconto_percentual);
        debugLog("✅ Checkbox Venda Comissionada:", vendaComissionada);
        debugLog("💼 Funcionário Comissão:", funcionarioComissao);
        debugLog("📋 Funcionário ID enviado:", funcionarioComissao?.id || null);

        if (vendaComissionada && !funcionarioComissao) {
          console.error(
            "⚠️ ERRO: Checkbox marcado mas funcionário não selecionado!",
          );
        }

        debugLog(
          "📦 PAYLOAD COMPLETO antes de enviar:",
          JSON.stringify(payloadVenda, null, 2),
        );
        debugLog("🚚 Dados de entrega:", {
          tem_entrega: payloadVenda.tem_entrega,
          entregador_id: payloadVenda.entregador_id,
          entregadorSelecionado: entregadorSelecionado?.id,
          vendaAtual_completo: vendaAtual,
        });
        debugLog("💰 Percentuais calculados:", payloadVenda);

        await criarVenda(payloadVenda);

        alert("Venda salva com sucesso!");
        limparVenda();
      }

      carregarVendasRecentes();
    } catch (error) {
      console.error("❌ Erro ao salvar venda:", error);
      console.error("❌ Resposta do servidor:", error.response?.data);
      console.error("❌ Status:", error.response?.status);
      console.error("❌ Headers:", error.response?.headers);
      const errorDetail =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        "Erro ao salvar venda";
      console.error("❌ Detalhes do erro:", errorDetail);
      alert(`Erro ao salvar venda: ${errorDetail}`);
    } finally {
      setLoading(false);
    }
  };

  return {
    salvarVenda,
  };
}
