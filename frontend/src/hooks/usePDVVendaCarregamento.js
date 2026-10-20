import { useRef } from "react";
import api from "../api";
import { buscarClientePorId } from "../api/clientes";
import { buscarVendaComSituacaoFiscal, listarVendas } from "../api/vendas";
import { debugLog } from "../utils/debug";
import { extrairCamposFiscaisVenda } from "../utils/pdvFiscalStatus";
import { perguntarCorePet } from "../services/corepetDialog";
import { obterTotalRecebidoExistente } from "../components/modalPagamentoUtils";
import { normalizarDescontosVenda } from "../utils/pdvDescontosUtils";

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
      totalPago: obterTotalRecebidoExistente(responsePagamentos.data),
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
  const carregamentosEmAndamentoRef = useRef(new Map());
  const selecaoAtualRef = useRef(null);

  const carregarVendaEspecifica = async (vendaId, abrirModalPagamento = false) => {
    const vendaIdNormalizado = Number.parseInt(vendaId, 10);
    if (!Number.isFinite(vendaIdNormalizado) || vendaIdNormalizado <= 0) {
      alert("Venda invalida");
      return;
    }

    const chaveCarregamento = String(vendaIdNormalizado);
    const carregamentoExistente = carregamentosEmAndamentoRef.current.get(chaveCarregamento);

    if (carregamentoExistente) {
      selecaoAtualRef.current = carregamentoExistente;
      setLoading(true);
      await carregamentoExistente.promise;
      if (selecaoAtualRef.current !== carregamentoExistente) return;
      setLoading(false);
      if (abrirModalPagamento) {
        setTimeout(() => {
          if (selecaoAtualRef.current === carregamentoExistente) setMostrarModalPagamento(true);
        }, 500);
      }
      return;
    }

    const selecao = {};
    selecaoAtualRef.current = selecao;
    const atual = () => selecaoAtualRef.current === selecao;
    const carregamento = (async () => {
      try {
        setLoading(true);
        const venda = normalizarDescontosVenda(
          await buscarVendaComSituacaoFiscal(vendaIdNormalizado),
        );
        if (!atual()) return;

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
        if (!atual()) return;

        const { pagamentos, totalPago } = await carregarPagamentosVenda(vendaIdNormalizado);
        if (!atual()) return;

        await sincronizarComissaoDaVenda(
          venda.vendedor_funcionario_id || venda.funcionario_id,
          venda.funcionario_id,
        );
        if (!atual()) return;

        const vendaCarregada = {
          id: venda.id,
          numero_venda: venda.numero_venda,
          status: venda.status,
          data_venda: venda.data_venda,
          canal: venda.canal || "loja_fisica",
          cliente: clienteCompleto,
          pet: null,
          itens: venda.itens || [],
          subtotal: venda.subtotal || 0,
          desconto_valor: venda.desconto_valor || 0,
          desconto_venda_valor: venda.desconto_venda_valor,
          desconto_origem_legado: venda.desconto_origem_legado,
          desconto_percentual: venda.desconto_percentual || 0,
          cupom_code: venda.cupom_code || null,
          cupom_discount_applied: venda.cupom_discount_applied ?? null,
          cupons_detalhes: venda.cupons_detalhes || [],
          total: venda.total || 0,
          observacoes: venda.observacoes || "",
          funcionario_id: venda.funcionario_id || null,
          vendedor_funcionario_id: venda.vendedor_funcionario_id || venda.funcionario_id || null,
          entregador_id: venda.entregador_id || null,
          tem_entrega: venda.tem_entrega || false,
          pagamento_entrega_previsto: venda.pagamento_entrega_previsto || null,
          entrega: venda.entrega || criarEntregaVazia(),
          pagamentos,
          total_pago: totalPago,
          ...extrairCamposFiscaisVenda(venda),
          nfe_atualizacao_falhou: Boolean(venda.nfe_atualizacao_falhou),
        };

        setVendaAtual(vendaCarregada);
        setModoVisualizacao(true);

        await sincronizarEntregadorDaVenda(venda.entregador_id);
        if (!atual()) return;
        await recarregarContextoClientePorId?.(clienteCompleto?.id || venda.cliente_id);
        if (!atual()) return;

        if (abrirModalPagamento) {
          setTimeout(() => {
            if (atual()) setMostrarModalPagamento(true);
          }, 500);
        }
      } catch (error) {
        if (!atual()) return;
        console.error("Erro ao carregar venda:", error);
        if (error.response?.status === 404) {
          alert("Venda nao encontrada. Pode ter sido cancelada ou excluida.");
        } else {
          alert("Erro ao carregar venda: " + (error.message || "Erro desconhecido"));
        }
      } finally {
        if (atual()) setLoading(false);
      }
    })();

    selecao.promise = carregamento;
    carregamentosEmAndamentoRef.current.set(chaveCarregamento, selecao);

    try {
      await carregamento;
    } finally {
      carregamentosEmAndamentoRef.current.delete(chaveCarregamento);
    }
  };

  const handleBuscarVenda = async () => {
    if (!searchVendaQuery.trim()) return;
    const selecao = {};
    selecaoAtualRef.current = selecao;
    const atual = () => selecaoAtualRef.current === selecao;

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
      if (!atual()) return;

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

      const numeroEscolhido = await perguntarCorePet(
        `Encontradas ${resultado.vendas.length} vendas. Digite o numero da opcao:\n\n${escolha}`,
      );
      if (!atual()) return;

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
      if (!atual()) return;
      console.error("Erro ao buscar venda:", error);
      alert("Erro ao buscar venda");
    } finally {
      if (atual()) setLoading(false);
    }
  };

  const reabrirVenda = async (venda) => {
    const selecao = {};
    selecaoAtualRef.current = selecao;
    const atual = () => selecaoAtualRef.current === selecao;
    try {
      setLoading(true);
      const vendaCompleta = normalizarDescontosVenda(await buscarVendaComSituacaoFiscal(venda.id));
      if (!atual()) return;

      let clienteCompleto = null;
      if (vendaCompleta.cliente_id) {
        clienteCompleto = await buscarClientePorId(vendaCompleta.cliente_id);
      }
      if (!atual()) return;

      const { pagamentos, totalPago } = await carregarPagamentosVenda(venda.id);
      if (!atual()) return;

      await sincronizarComissaoDaVenda(
        vendaCompleta.vendedor_funcionario_id || vendaCompleta.funcionario_id,
        vendaCompleta.funcionario_id,
      );
      if (!atual()) return;

      const vendaParaSetar = {
        id: vendaCompleta.id,
        numero_venda: vendaCompleta.numero_venda,
        data_venda: vendaCompleta.data_venda,
        canal: vendaCompleta.canal || "loja_fisica",
        cliente: clienteCompleto,
        pet: null,
        itens: vendaCompleta.itens || [],
        subtotal: parseFloat(vendaCompleta.subtotal || vendaCompleta.total),
        desconto_valor: parseFloat(vendaCompleta.desconto_valor || 0),
        desconto_venda_valor: vendaCompleta.desconto_venda_valor,
        desconto_origem_legado: vendaCompleta.desconto_origem_legado,
        desconto_percentual: parseFloat(vendaCompleta.desconto_percentual || 0),
        cupom_code: vendaCompleta.cupom_code || null,
        cupom_discount_applied: vendaCompleta.cupom_discount_applied ?? null,
        cupons_detalhes: vendaCompleta.cupons_detalhes || [],
        total: parseFloat(vendaCompleta.total),
        observacoes: vendaCompleta.observacoes || "",
        status: vendaCompleta.status,
        funcionario_id: vendaCompleta.funcionario_id || null,
        vendedor_funcionario_id:
          vendaCompleta.vendedor_funcionario_id || vendaCompleta.funcionario_id || null,
        tem_entrega: vendaCompleta.tem_entrega || false,
        pagamento_entrega_previsto: vendaCompleta.pagamento_entrega_previsto || null,
        entregador_id: vendaCompleta.entregador_id || null,
        entrega: {
          endereco_completo: vendaCompleta.endereco_entrega || "",
          endereco_id: vendaCompleta.endereco_id || null,
          taxa_entrega_total: parseFloat(parseFloat(vendaCompleta.taxa_entrega || 0).toFixed(2)),
          taxa_loja: parseFloat(parseFloat(vendaCompleta.entrega?.taxa_loja || 0).toFixed(2)),
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
        ...extrairCamposFiscaisVenda(vendaCompleta),
        nfe_atualizacao_falhou: Boolean(vendaCompleta.nfe_atualizacao_falhou),
      };

      setVendaAtual(vendaParaSetar);
      setModoVisualizacao(true);
      await recarregarContextoClientePorId?.(clienteCompleto?.id || vendaCompleta.cliente_id);
      if (!atual()) return;
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      if (!atual()) return;
      console.error("Erro ao reabrir venda:", error);
      alert("Erro ao carregar os dados da venda");
    } finally {
      if (atual()) setLoading(false);
    }
  };

  return {
    carregarVendaEspecifica,
    handleBuscarVenda,
    reabrirVenda,
  };
}
