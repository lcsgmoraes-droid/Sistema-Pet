import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import { extrairMensagemErroApiMovimentacao as extrairMensagemErroApi } from "./movimentacoesProdutoUtils";

const MOVIMENTACOES_POR_PAGINA = 50;

function normalizarPaginaMovimentacoes(payload, pagina, pageSize) {
  if (Array.isArray(payload)) {
    return {
      movimentacoes: payload,
      totalRegistros: payload.length,
      pagina: 1,
      pageSize: payload.length || pageSize,
      pages: payload.length > 0 ? 1 : 0,
      totalEntradas: payload
        .filter((item) => item.tipo === "entrada" && item.status !== "cancelado")
        .reduce((total, item) => total + Number(item.quantidade || 0), 0),
      totalSaidas: payload
        .filter((item) => item.tipo === "saida" && item.status !== "cancelado")
        .reduce((total, item) => total + Number(item.quantidade || 0), 0),
    };
  }

  return {
    movimentacoes: Array.isArray(payload?.movimentacoes) ? payload.movimentacoes : [],
    totalRegistros: Number(payload?.total_registros || 0),
    pagina: Number(payload?.page || pagina),
    pageSize: Number(payload?.page_size || pageSize),
    pages: Number(payload?.pages || 0),
    totalEntradas: Number(payload?.totais?.total_entradas || 0),
    totalSaidas: Number(payload?.totais?.total_saidas || 0),
  };
}

export default function useMovimentacoesProdutoListagem({ id, moduloBlingAtivo }) {
  const [produto, setProduto] = useState(null);
  const [movimentacoes, setMovimentacoes] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMovimentacoes, setLoadingMovimentacoes] = useState(false);
  const [loadingVendasPorCanal, setLoadingVendasPorCanal] = useState(false);
  const [vendasPorCanal, setVendasPorCanal] = useState([]);
  const [paginaMovimentacoes, setPaginaMovimentacoes] = useState(1);
  const [movimentacoesPorPagina, setMovimentacoesPorPagina] = useState(MOVIMENTACOES_POR_PAGINA);
  const [totalMovimentacoes, setTotalMovimentacoes] = useState(0);
  const [totalPaginasMovimentacoes, setTotalPaginasMovimentacoes] = useState(0);
  const [totalEntradas, setTotalEntradas] = useState(0);
  const [totalSaidas, setTotalSaidas] = useState(0);
  const [syncProduto, setSyncProduto] = useState(null);

  const aplicarPaginaMovimentacoes = (payload, pagina, pageSize) => {
    const dados = normalizarPaginaMovimentacoes(payload, pagina, pageSize);
    setMovimentacoes(dados.movimentacoes);
    setTotalMovimentacoes(dados.totalRegistros);
    setPaginaMovimentacoes(dados.pagina);
    setMovimentacoesPorPagina(dados.pageSize);
    setTotalPaginasMovimentacoes(dados.pages);
    setTotalEntradas(dados.totalEntradas);
    setTotalSaidas(dados.totalSaidas);
    setSelectedIds([]);
  };

  const carregarStatusSyncProduto = async (produtoData) => {
    const termoBuscaSync = produtoData?.codigo || produtoData?.sku;
    if (!moduloBlingAtivo || !termoBuscaSync) {
      setSyncProduto(null);
      return;
    }

    try {
      const syncRes = await api.get("/estoque/sync/status", {
        params: { busca: termoBuscaSync },
      });
      const itemSync = (syncRes.data || []).find((item) => item.produto_id === Number(id));
      setSyncProduto(itemSync || null);
    } catch (syncError) {
      if (syncError?.response?.status !== 403) {
        console.warn("Nao foi possivel carregar status de sincronizacao:", syncError);
      }
      setSyncProduto(null);
    }
  };

  const carregarVendasPorCanal = async () => {
    try {
      setLoadingVendasPorCanal(true);
      const response = await api.get(`/estoque/movimentacoes/produto/${id}/vendas-por-canal`);
      setVendasPorCanal(
        Array.isArray(response?.data?.vendas_por_canal) ? response.data.vendas_por_canal : [],
      );
    } catch (error) {
      console.warn("Nao foi possivel carregar o resumo de vendas por canal:", error);
      setVendasPorCanal([]);
    } finally {
      setLoadingVendasPorCanal(false);
    }
  };

  const carregarPaginaMovimentacoes = async (pagina, pageSize = movimentacoesPorPagina) => {
    try {
      setLoadingMovimentacoes(true);
      const response = await api.get(`/estoque/movimentacoes/produto/${id}`, {
        params: { page: pagina, page_size: pageSize },
      });
      aplicarPaginaMovimentacoes(response.data, pagina, pageSize);
    } catch (error) {
      console.error("Erro ao carregar movimentacoes:", error);
      toast.error(extrairMensagemErroApi(error, "Erro ao carregar movimentacoes do produto"));
    } finally {
      setLoadingMovimentacoes(false);
    }
  };

  const carregarDados = async ({
    pagina = paginaMovimentacoes,
    pageSize = movimentacoesPorPagina,
  } = {}) => {
    try {
      setLoadingMovimentacoes(true);
      const [produtoRes, movRes] = await Promise.all([
        api.get(`/produtos/${id}`),
        api.get(`/estoque/movimentacoes/produto/${id}`, {
          params: { page: pagina, page_size: pageSize },
        }),
      ]);

      const produtoData = produtoRes.data;
      setProduto(produtoData);
      aplicarPaginaMovimentacoes(movRes.data, pagina, pageSize);
      void carregarStatusSyncProduto(produtoData);
      void carregarVendasPorCanal();
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      console.error("Detalhes do erro:", error.response?.data);
      toast.error(extrairMensagemErroApi(error, "Erro ao carregar dados do produto"));
    } finally {
      setLoading(false);
      setLoadingMovimentacoes(false);
    }
  };

  useEffect(() => {
    setPaginaMovimentacoes(1);
    void carregarDados({ pagina: 1, pageSize: movimentacoesPorPagina });
  }, [id, moduloBlingAtivo]);

  return {
    carregarDados,
    carregarPaginaMovimentacoes,
    loading,
    loadingMovimentacoes,
    loadingVendasPorCanal,
    movimentacoes,
    movimentacoesPorPagina,
    paginaMovimentacoes,
    produto,
    selectedIds,
    setMovimentacoesPorPagina,
    setPaginaMovimentacoes,
    setSelectedIds,
    syncProduto,
    totalEntradas,
    totalMovimentacoes,
    totalPaginasMovimentacoes,
    totalSaidas,
    vendasPorCanal,
  };
}
