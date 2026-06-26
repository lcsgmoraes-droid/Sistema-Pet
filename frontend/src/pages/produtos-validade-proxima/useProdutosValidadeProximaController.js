import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { getRelatorioValidadeProxima } from "../../api/produtos";
import {
  criarExclusaoCampanhaValidade,
  removerExclusaoCampanhaValidade,
} from "../../api/campanhasValidade";
import { getFornecedorNome } from "../../components/fornecedores/FornecedorSelector";
import useProdutosCatalogos from "../../hooks/useProdutosCatalogos";
import {
  ITENS_POR_PAGINA_INICIAL,
  QUICK_DAYS,
  criarDadosValidadeVazios,
  filtrosIniciais,
  montarParametros,
} from "./produtosValidadeProximaConstants";
import { exportarCsvValidade } from "./produtosValidadeProximaCsv";
import { getDiasRestantesVisual } from "./produtosValidadeProximaFormatters";

export default function useProdutosValidadeProximaController({ reloadSignal = 0 } = {}) {
  const navigate = useNavigate();
  const catalogos = useProdutosCatalogos();
  const [loading, setLoading] = useState(false);
  const [exportando, setExportando] = useState(false);
  const [acaoCampanhaLoteId, setAcaoCampanhaLoteId] = useState(null);
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [filtrosForm, setFiltrosForm] = useState(filtrosIniciais);
  const [filtrosAplicados, setFiltrosAplicados] = useState(filtrosIniciais);
  const [dados, setDados] = useState(() => criarDadosValidadeVazios());

  const carregarRelatorio = useCallback(async (filtros, pagina) => {
    try {
      setLoading(true);
      const response = await getRelatorioValidadeProxima(montarParametros(filtros, pagina));
      setDados(response.data);
    } catch (error) {
      console.error("Erro ao carregar validade proxima:", error);
      toast.error(
        error?.response?.data?.detail || "Nao foi possivel carregar os lotes com validade proxima.",
      );
      setDados(criarDadosValidadeVazios(Number(filtros.page_size) || ITENS_POR_PAGINA_INICIAL));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void carregarRelatorio(filtrosAplicados, paginaAtual);
  }, [carregarRelatorio, filtrosAplicados, paginaAtual, reloadSignal]);

  const atualizarFiltro = useCallback((campo, valor) => {
    setFiltrosForm((prev) => ({ ...prev, [campo]: valor }));
  }, []);

  const fornecedorFiltroSelecionado = useMemo(
    () =>
      catalogos.fornecedores.find(
        (fornecedor) => String(fornecedor.id) === String(filtrosForm.fornecedor_id),
      ) || null,
    [catalogos.fornecedores, filtrosForm.fornecedor_id],
  );

  const selecionarFornecedorFiltro = useCallback((fornecedor) => {
    setFiltrosForm((prev) => ({
      ...prev,
      fornecedor_id: fornecedor?.id ? String(fornecedor.id) : "",
      fornecedor_busca: getFornecedorNome(fornecedor),
    }));
  }, []);

  const alterarFornecedorBusca = useCallback((termo) => {
    setFiltrosForm((prev) => ({
      ...prev,
      fornecedor_id: "",
      fornecedor_busca: termo,
    }));
  }, []);

  const limparFornecedorFiltro = useCallback(() => {
    setFiltrosForm((prev) => ({
      ...prev,
      fornecedor_id: "",
      fornecedor_busca: "",
    }));
  }, []);

  const aplicarFiltros = useCallback(
    (event) => {
      event.preventDefault();
      setPaginaAtual(1);
      setFiltrosAplicados({
        ...filtrosForm,
        dias: Number(filtrosForm.dias) || 60,
        page_size: Number(filtrosForm.page_size) || ITENS_POR_PAGINA_INICIAL,
      });
    },
    [filtrosForm],
  );

  const limparFiltros = useCallback(() => {
    setPaginaAtual(1);
    setFiltrosForm(filtrosIniciais);
    setFiltrosAplicados(filtrosIniciais);
  }, []);

  const exportarCsv = useCallback(async () => {
    try {
      setExportando(true);
      await exportarCsvValidade(filtrosAplicados);
    } catch (error) {
      console.error("Erro ao exportar CSV de validade:", error);
      toast.error("Nao foi possivel gerar o CSV de validade.", { id: "csv-validade" });
    } finally {
      setExportando(false);
    }
  }, [filtrosAplicados]);

  const items = Array.isArray(dados.items) ? dados.items : [];
  const inicioItem = dados.total === 0 ? 0 : (dados.page - 1) * dados.page_size + 1;
  const fimItem = dados.total === 0 ? 0 : Math.min(dados.page * dados.page_size, dados.total);
  const totalPaginas = dados.pages || 0;
  const loteMaisUrgente = useMemo(() => {
    if (!items.length) return null;

    return items.reduce((maisUrgente, itemAtual) => {
      const diasMaisUrgente = Number(maisUrgente?.dias_para_vencer ?? Infinity);
      const diasAtual = Number(itemAtual?.dias_para_vencer ?? Infinity);
      return diasAtual < diasMaisUrgente ? itemAtual : maisUrgente;
    }, items[0]);
  }, [items]);
  const prazoMaisCurto = loteMaisUrgente
    ? getDiasRestantesVisual(loteMaisUrgente.dias_para_vencer)
    : null;

  const atualizarPainelAtual = useCallback(
    () => carregarRelatorio(filtrosAplicados, paginaAtual),
    [carregarRelatorio, filtrosAplicados, paginaAtual],
  );

  const excluirDaCampanha = useCallback(
    async (item) => {
      try {
        setAcaoCampanhaLoteId(item.lote_id);
        await criarExclusaoCampanhaValidade({
          produto_id: item.produto_id,
          lote_id: item.lote_id,
          motivo: "Remocao manual da campanha de validade",
          observacao: `Lote ${item.nome_lote} removido manualmente pela tela de validade.`,
        });
        toast.success("Lote removido da campanha automatica.");
        await atualizarPainelAtual();
      } catch (error) {
        console.error("Erro ao excluir lote da campanha:", error);
        toast.error(
          error?.response?.data?.detail || "Nao foi possivel remover o lote da campanha.",
        );
      } finally {
        setAcaoCampanhaLoteId(null);
      }
    },
    [atualizarPainelAtual],
  );

  const reincluirNaCampanha = useCallback(
    async (item) => {
      if (!item.campanha_validade_exclusao_id) return;
      try {
        setAcaoCampanhaLoteId(item.lote_id);
        await removerExclusaoCampanhaValidade(item.campanha_validade_exclusao_id);
        toast.success("Lote reincluido na campanha automatica.");
        await atualizarPainelAtual();
      } catch (error) {
        console.error("Erro ao reincluir lote na campanha:", error);
        toast.error(
          error?.response?.data?.detail || "Nao foi possivel reincluir o lote na campanha.",
        );
      } finally {
        setAcaoCampanhaLoteId(null);
      }
    },
    [atualizarPainelAtual],
  );

  const irParaCampanhas = useCallback(() => navigate("/campanhas?aba=validade"), [navigate]);
  const irParaProdutos = useCallback(() => navigate("/produtos"), [navigate]);
  const editarProduto = useCallback(
    (item) => navigate(`/produtos/${item.produto_id}/editar`),
    [navigate],
  );

  return {
    catalogos,
    dados: { ...dados, items },
    loading,
    exportando,
    acaoCampanhaLoteId,
    paginaAtual,
    filtrosForm,
    fornecedorFiltroSelecionado,
    inicioItem,
    fimItem,
    totalPaginas,
    loteMaisUrgente,
    prazoMaisCurto,
    quickDays: QUICK_DAYS,
    atualizarFiltro,
    selecionarFornecedorFiltro,
    alterarFornecedorBusca,
    limparFornecedorFiltro,
    aplicarFiltros,
    limparFiltros,
    exportarCsv,
    setPaginaAtual,
    excluirDaCampanha,
    reincluirNaCampanha,
    irParaCampanhas,
    irParaProdutos,
    editarProduto,
  };
}
