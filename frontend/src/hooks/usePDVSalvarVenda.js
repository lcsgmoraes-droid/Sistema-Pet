import api from "../api";
import { criarVenda } from "../api/vendas";
import { debugLog } from "../utils/debug";

function montarItensPayload(vendaAtual) {
  return vendaAtual.itens.map((item) => ({
    tipo: item.tipo,
    produto_id: item.produto_id,
    servico_descricao: item.servico_descricao,
    quantidade: item.quantidade,
    preco_unitario: item.preco_unitario || item.preco_venda,
    desconto_item: 0,
    subtotal: item.subtotal,
    lote_id: item.lote_id,
    pet_id: item.pet_id || vendaAtual.pet?.id,
  }));
}

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
      const entregadorIdResolvido =
        vendaAtual.entregador_id || entregadorSelecionado?.id || null;

      if (vendaAtual.id) {
        await api.put(`/vendas/${vendaAtual.id}`, {
          cliente_id: vendaAtual.cliente?.id,
          funcionario_id: vendaAtual.funcionario_id,
          itens: montarItensPayload(vendaAtual),
          desconto_valor: 0,
          desconto_percentual: 0,
          observacoes: vendaAtual.observacoes,
          tem_entrega: vendaAtual.tem_entrega,
          taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
          endereco_entrega: vendaAtual.entrega?.endereco_completo,
          observacoes_entrega: vendaAtual.entrega?.observacoes_entrega,
          distancia_km: vendaAtual.entrega?.distancia_km,
          valor_por_km: vendaAtual.entrega?.valor_por_km,
          loja_origem: vendaAtual.entrega?.loja_origem,
          entregador_id: entregadorIdResolvido,
        });

        debugLog("🚨 DEBUG - Payload sendo enviado:", {
          tem_entrega: vendaAtual.tem_entrega,
          entregador_id: entregadorIdResolvido,
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
        debugLog("🚀 CRIANDO VENDA - Versão 2.0 - DESCONTOS ZERADOS");
        debugLog("Desconto valor:", 0);
        debugLog("Desconto percentual:", 0);
        debugLog("✅ Checkbox Venda Comissionada:", vendaComissionada);
        debugLog("💼 Funcionário Comissão:", funcionarioComissao);
        debugLog("📋 Funcionário ID enviado:", funcionarioComissao?.id || null);

        if (vendaComissionada && !funcionarioComissao) {
          console.error(
            "⚠️ ERRO: Checkbox marcado mas funcionário não selecionado!",
          );
        }

        const taxaTotal = vendaAtual.entrega?.taxa_entrega_total || 0;
        const taxaLoja = vendaAtual.entrega?.taxa_loja || 0;
        const taxaEntregador = vendaAtual.entrega?.taxa_entregador || 0;
        const percentualLoja =
          taxaTotal > 0 ? (taxaLoja / taxaTotal) * 100 : 100;
        const percentualEntregador =
          taxaTotal > 0 ? (taxaEntregador / taxaTotal) * 100 : 0;

        const payloadVenda = {
          cliente_id: vendaAtual.cliente?.id,
          funcionario_id: vendaAtual.funcionario_id,
          itens: montarItensPayload(vendaAtual),
          desconto_valor: 0,
          desconto_percentual: 0,
          observacoes: vendaAtual.observacoes,
          tem_entrega: vendaAtual.tem_entrega,
          taxa_entrega: vendaAtual.entrega?.taxa_entrega_total || 0,
          percentual_taxa_loja: percentualLoja,
          percentual_taxa_entregador: percentualEntregador,
          endereco_entrega: vendaAtual.entrega?.endereco_completo,
          observacoes_entrega: vendaAtual.entrega?.observacoes_entrega,
          distancia_km: vendaAtual.entrega?.distancia_km,
          valor_por_km: vendaAtual.entrega?.valor_por_km,
          loja_origem: vendaAtual.entrega?.loja_origem,
          entregador_id: entregadorIdResolvido,
        };

        debugLog(
          "📦 PAYLOAD COMPLETO antes de enviar:",
          JSON.stringify(payloadVenda, null, 2),
        );
        debugLog("🚚 Dados de entrega:", {
          tem_entrega: vendaAtual.tem_entrega,
          entregador_id: entregadorIdResolvido,
          entregadorSelecionado: entregadorSelecionado?.id,
          vendaAtual_completo: vendaAtual,
        });
        debugLog("💰 Percentuais calculados:", {
          taxaTotal,
          taxaLoja,
          taxaEntregador,
          percentualLoja: `${percentualLoja.toFixed(2)}%`,
          percentualEntregador: `${percentualEntregador.toFixed(2)}%`,
        });

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
