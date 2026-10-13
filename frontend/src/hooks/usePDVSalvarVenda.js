import api from "../api";
import { atualizarVenda, criarVenda, finalizarVenda } from "../api/vendas";
import { toast } from "react-hot-toast";
import { montarPayloadVenda } from "../utils/pdvVendaPayload";
import { debugLog } from "../utils/debug";
import { montarVendaPersistidaParaEdicao, salvarEdicaoVenda } from "../utils/pdvSalvarEdicaoVenda";

export function usePDVSalvarVenda({
  vendaAtual,
  setVendaAtual,
  loading,
  setLoading,
  temCaixaAberto,
  entregadorSelecionado,
  vendaComissionada,
  vendedorObrigatorio,
  gerarComissao,
  funcionarioComissao,
  limparVenda,
  carregarVendasRecentes,
  recarregarContextoClienteAtual,
}) {
  const salvarVenda = async () => {
    if (vendaAtual.itens.length === 0) {
      toast.error("Adicione pelo menos um produto ou serviço.");
      return;
    }

    if (!temCaixaAberto) {
      toast.error("Não é possível salvar uma venda sem caixa aberto. Abra um caixa primeiro.");
      return;
    }

    if (vendedorObrigatorio === null) {
      toast.error("Aguarde o carregamento das regras do PDV.");
      return;
    }

    if ((vendaComissionada || vendedorObrigatorio) && !funcionarioComissao) {
      toast.error("Selecione o vendedor antes de salvar a venda.");
      return;
    }

    if (loading) return;

    setLoading(true);
    try {
      const vendaParaPayload = {
        ...vendaAtual,
        vendedor_funcionario_id:
          vendaComissionada || vendedorObrigatorio ? funcionarioComissao?.id || null : null,
        funcionario_id:
          (vendaComissionada || vendedorObrigatorio) && gerarComissao
            ? funcionarioComissao?.id || null
            : null,
      };
      const payloadVenda = montarPayloadVenda(vendaParaPayload, entregadorSelecionado);

      if (vendaAtual.id) {
        const resultado = await salvarEdicaoVenda({
          vendaAtual,
          payloadVenda,
          atualizarVenda,
          buscarPagamentos: async (vendaId) =>
            (await api.get(`/vendas/${vendaId}/pagamentos`)).data,
          finalizarVenda,
          onVendaPersistida: (persistida) =>
            setVendaAtual((prev) =>
              prev.id === persistida.id ? montarVendaPersistidaParaEdicao(prev, persistida) : prev,
            ),
        });

        debugLog("🚨 DEBUG - Payload sendo enviado:", {
          payload: payloadVenda,
          vendaAtual_completo: vendaAtual,
        });

        if (resultado.finalizada) {
          await recarregarContextoClienteAtual?.();
          toast.success("Venda atualizada e finalizada com os pagamentos já registrados.");
          limparVenda();
        } else {
          setVendaAtual((prev) =>
            prev.id === resultado.venda.id
              ? montarVendaPersistidaParaEdicao(
                  prev,
                  { ...resultado.venda, status: "aberta" },
                  resultado.recebido,
                )
              : prev,
          );
          toast.success("Alterações salvas. Registre o saldo restante para finalizar a venda.");
        }
      } else {
        debugLog("🚀 CRIANDO VENDA - payload consolidado");
        debugLog("Desconto valor:", payloadVenda.desconto_valor);
        debugLog("Desconto percentual:", payloadVenda.desconto_percentual);
        debugLog("✅ Checkbox Venda Comissionada:", vendaComissionada);
        debugLog("💼 Funcionário Comissão:", funcionarioComissao);
        debugLog("📋 Funcionário ID enviado:", funcionarioComissao?.id || null);

        if (vendaComissionada && !funcionarioComissao) {
          console.error("⚠️ ERRO: Checkbox marcado mas funcionário não selecionado!");
        }

        debugLog("📦 PAYLOAD COMPLETO antes de enviar:", JSON.stringify(payloadVenda, null, 2));
        debugLog("🚚 Dados de entrega:", {
          tem_entrega: payloadVenda.tem_entrega,
          entregador_id: payloadVenda.entregador_id,
          entregadorSelecionado: entregadorSelecionado?.id,
          vendaAtual_completo: vendaAtual,
        });
        debugLog("💰 Percentuais calculados:", payloadVenda);

        await criarVenda(payloadVenda);

        toast.success("Venda salva! Ela já aparece em Vendas Recentes.");
        limparVenda();
      }

      carregarVendasRecentes();
    } catch (error) {
      console.error("❌ Erro ao salvar venda:", error);
      console.error("❌ Resposta do servidor:", error.response?.data);
      console.error("❌ Status:", error.response?.status);
      console.error("❌ Headers:", error.response?.headers);
      const errorDetail =
        error.response?.data?.detail || error.response?.data?.message || "Erro ao salvar venda";
      console.error("❌ Detalhes do erro:", errorDetail);
      toast.error(`Erro ao salvar venda: ${errorDetail}`);
    } finally {
      setLoading(false);
    }
  };

  return {
    salvarVenda,
  };
}
