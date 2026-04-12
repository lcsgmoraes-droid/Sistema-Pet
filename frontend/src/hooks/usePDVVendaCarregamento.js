import api from "../api";
import { buscarClientePorId } from "../api/clientes";
import { buscarVenda, listarVendas } from "../api/vendas";
import { debugLog } from "../utils/debug";

function criarEntregaVazia() {
  return {
    endereco_completo: "",
    taxa_entrega_total: 0,
    taxa_loja: 0,
    taxa_entregador: 0,
    observacoes_entrega: "",
  };
}

async function carregarPagamentosVenda(vendaId) {
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

export function usePDVVendaCarregamento({
  setVendaAtual,
  searchVendaQuery,
  setSearchVendaQuery,
  setLoading,
  setModoVisualizacao,
  setMostrarModalPagamento,
  sincronizarComissaoDaVenda,
  sincronizarEntregadorDaVenda,
  recarregarContextoClientePorId,
}) {
  const carregarVendaEspecifica = async (
    vendaId,
    abrirModalPagamento = false,
  ) => {
    try {
      setLoading(true);
      const venda = await buscarVenda(vendaId);

      if (!venda) {
        alert("Venda nao encontrada");
        return;
      }

      let clienteCompleto = null;
      if (venda.cliente_id) {
        try {
          clienteCompleto = await buscarClientePorId(venda.cliente_id);
        } catch (error) {
          console.error("Erro ao buscar cliente:", error);
        }
      }

      const { pagamentos, totalPago } = await carregarPagamentosVenda(vendaId);

      await sincronizarComissaoDaVenda(venda.funcionario_id);

      const vendaCarregada = {
        id: venda.id,
        numero_venda: venda.numero_venda,
        status: venda.status,
        data_venda: venda.data_venda,
        cliente: clienteCompleto,
        pet: null,
        itens: venda.itens || [],
        subtotal: venda.subtotal || 0,
        desconto_valor: venda.desconto_valor || 0,
        desconto_percentual: venda.desconto_percentual || 0,
        total: venda.total || 0,
        observacoes: venda.observacoes || "",
        funcionario_id: venda.funcionario_id || null,
        entregador_id: venda.entregador_id || null,
        tem_entrega: venda.tem_entrega || false,
        entrega: venda.entrega || criarEntregaVazia(),
        pagamentos,
        total_pago: totalPago,
      };

      setVendaAtual(vendaCarregada);
      setModoVisualizacao(true);

      await sincronizarEntregadorDaVenda(venda.entregador_id);
      await recarregarContextoClientePorId?.(clienteCompleto?.id || venda.cliente_id);

      if (abrirModalPagamento) {
        setTimeout(() => {
          setMostrarModalPagamento(true);
        }, 500);
      }
    } catch (error) {
      console.error("Erro ao carregar venda:", error);
      if (error.response?.status === 404) {
        alert("Venda nao encontrada. Pode ter sido cancelada ou excluida.");
      } else {
        alert(
          "Erro ao carregar venda: " + (error.message || "Erro desconhecido"),
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBuscarVenda = async () => {
    if (!searchVendaQuery.trim()) return;

    try {
      setLoading(true);

      const numeroLimpo = searchVendaQuery.replace(/\D/g, "");

      if (!numeroLimpo) {
        alert("Digite um numero de venda valido");
        setLoading(false);
        return;
      }

      debugLog("Buscando venda com numero:", numeroLimpo);

      const resultado = await listarVendas({
        busca: numeroLimpo,
        per_page: 50,
      });

      debugLog("Vendas encontradas:", resultado.vendas?.length);

      if (!resultado.vendas || resultado.vendas.length === 0) {
        alert(`Nenhuma venda encontrada com "${numeroLimpo}"`);
        setLoading(false);
        return;
      }

      if (resultado.vendas.length === 1) {
        await carregarVendaEspecifica(resultado.vendas[0].id);
        setSearchVendaQuery("");
        return;
      }

      const escolha = resultado.vendas
        .slice(0, 10)
        .map(
          (venda, index) =>
            `${index + 1}. ${venda.numero_venda} - ${venda.cliente_nome || "Sem cliente"} - ${venda.status}`,
        )
        .join("\n");

      const numeroEscolhido = prompt(
        `Encontradas ${resultado.vendas.length} vendas. Digite o numero da opcao:\n\n${escolha}`,
      );

      if (!numeroEscolhido) {
        setLoading(false);
        return;
      }

      const indice = Number.parseInt(numeroEscolhido, 10) - 1;

      if (indice >= 0 && indice < resultado.vendas.length) {
        await carregarVendaEspecifica(resultado.vendas[indice].id);
        setSearchVendaQuery("");
      } else {
        alert("Opcao invalida");
      }
    } catch (error) {
      console.error("Erro ao buscar venda:", error);
      alert("Erro ao buscar venda");
    } finally {
      setLoading(false);
    }
  };

  const reabrirVenda = async (venda) => {
    try {
      const vendaCompleta = await buscarVenda(venda.id);

      let clienteCompleto = null;
      if (vendaCompleta.cliente_id) {
        clienteCompleto = await buscarClientePorId(vendaCompleta.cliente_id);
      }

      const { pagamentos, totalPago } = await carregarPagamentosVenda(venda.id);

      await sincronizarComissaoDaVenda(vendaCompleta.funcionario_id);

      const vendaParaSetar = {
        id: vendaCompleta.id,
        numero_venda: vendaCompleta.numero_venda,
        data_venda: vendaCompleta.data_venda,
        cliente: clienteCompleto,
        pet: null,
        itens: vendaCompleta.itens || [],
        subtotal: parseFloat(vendaCompleta.subtotal || vendaCompleta.total),
        desconto_valor: parseFloat(vendaCompleta.desconto_valor || 0),
        desconto_percentual: parseFloat(
          vendaCompleta.desconto_percentual || 0,
        ),
        total: parseFloat(vendaCompleta.total),
        observacoes: vendaCompleta.observacoes || "",
        status: vendaCompleta.status,
        tem_entrega: vendaCompleta.tem_entrega || false,
        entregador_id: vendaCompleta.entregador_id || null,
        entrega: {
          endereco_completo: vendaCompleta.endereco_entrega || "",
          endereco_id: vendaCompleta.endereco_id || null,
          taxa_entrega_total: parseFloat(
            parseFloat(vendaCompleta.taxa_entrega || 0).toFixed(2),
          ),
          taxa_loja: parseFloat(
            parseFloat(vendaCompleta.entrega?.taxa_loja || 0).toFixed(2),
          ),
          taxa_entregador: parseFloat(
            parseFloat(vendaCompleta.entrega?.taxa_entregador || 0).toFixed(2),
          ),
          observacoes_entrega: vendaCompleta.observacoes_entrega || "",
          distancia_km: vendaCompleta.distancia_km || 0,
          valor_por_km: vendaCompleta.valor_por_km || 0,
          loja_origem: vendaCompleta.loja_origem || "",
          status_entrega: vendaCompleta.status_entrega || "pendente",
        },
        pagamentos,
        total_pago: totalPago,
      };

      setVendaAtual(vendaParaSetar);
      setModoVisualizacao(true);
      await recarregarContextoClientePorId?.(
        clienteCompleto?.id || vendaCompleta.cliente_id,
      );
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      console.error("Erro ao reabrir venda:", error);
      alert("Erro ao carregar os dados da venda");
    }
  };

  return {
    carregarVendaEspecifica,
    handleBuscarVenda,
    reabrirVenda,
  };
}
