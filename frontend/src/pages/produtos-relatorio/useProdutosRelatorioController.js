import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import {
  getProdutos,
  getRelatorioMovimentacoes,
  getRelatorioProdutoVendas,
} from "../../api/produtos";
import {
  ITENS_HISTORICO_VENDAS,
  ITENS_POR_PAGINA_INICIAL,
  PERIODOS,
} from "./produtosRelatorioConstants";
import {
  criarDadosMovimentacoesVazios,
  criarFiltrosPadrao,
  montarParamsMovimentacoes,
  normalizarDadosMovimentacoes,
} from "./produtosRelatorioData";
import { dataInicioPorDias, extrairListaProdutos, hojeIso } from "./produtosRelatorioFormatters";

export default function useProdutosRelatorioController() {
  const navigate = useNavigate();
  const buscaRef = useRef(null);
  const filtrosPadrao = useMemo(criarFiltrosPadrao, []);
  const [periodoSelecionado, setPeriodoSelecionado] = useState("30dias");
  const [filtrosForm, setFiltrosForm] = useState(filtrosPadrao);
  const [filtrosAplicados, setFiltrosAplicados] = useState(filtrosPadrao);
  const [produtoSelecionado, setProdutoSelecionado] = useState(null);
  const [buscaProduto, setBuscaProduto] = useState("");
  const [sugestoesProdutos, setSugestoesProdutos] = useState([]);
  const [dropdownAberto, setDropdownAberto] = useState(false);
  const [loadingBuscaProduto, setLoadingBuscaProduto] = useState(false);
  const [loadingMovimentacoes, setLoadingMovimentacoes] = useState(false);
  const [loadingResumoProduto, setLoadingResumoProduto] = useState(false);
  const [exportando, setExportando] = useState(false);
  const [paginaMovimentacoes, setPaginaMovimentacoes] = useState(1);
  const [paginaHistoricoVendas, setPaginaHistoricoVendas] = useState(1);
  const [dadosMovimentacoes, setDadosMovimentacoes] = useState(() =>
    criarDadosMovimentacoesVazios(),
  );
  const [dadosProduto, setDadosProduto] = useState(null);

  const produtoAtivoId = filtrosAplicados.produto_id || "";
  const periodoAtivoDias = useMemo(
    () => PERIODOS.find((periodo) => periodo.value === periodoSelecionado)?.dias,
    [periodoSelecionado],
  );

  const carregarMovimentacoes = useCallback(async (filtros, pagina) => {
    try {
      setLoadingMovimentacoes(true);
      const response = await getRelatorioMovimentacoes(montarParamsMovimentacoes(filtros, pagina));
      setDadosMovimentacoes(normalizarDadosMovimentacoes(response?.data || {}, filtros, pagina));
    } catch (error) {
      console.error("Erro ao carregar movimentacoes:", error);
      toast.error(error?.response?.data?.detail || "Nao foi possivel carregar as movimentacoes.");
      setDadosMovimentacoes(criarDadosMovimentacoesVazios(filtros.page_size));
    } finally {
      setLoadingMovimentacoes(false);
    }
  }, []);

  const carregarResumoProduto = useCallback(async (filtros, pagina) => {
    try {
      setLoadingResumoProduto(true);
      const response = await getRelatorioProdutoVendas({
        produto_id: filtros.produto_id,
        data_inicio: filtros.data_inicio,
        data_fim: filtros.data_fim,
        page: pagina,
        page_size: ITENS_HISTORICO_VENDAS,
      });
      setDadosProduto(response?.data || null);
    } catch (error) {
      console.error("Erro ao carregar resumo do produto:", error);
      toast.error(
        error?.response?.data?.detail || "Nao foi possivel carregar o historico do produto.",
      );
      setDadosProduto(null);
    } finally {
      setLoadingResumoProduto(false);
    }
  }, []);

  useEffect(() => {
    const termo = buscaProduto.trim();
    if (produtoSelecionado || termo.length < 2) {
      setSugestoesProdutos([]);
      setLoadingBuscaProduto(false);
      return undefined;
    }

    const timer = setTimeout(async () => {
      try {
        setLoadingBuscaProduto(true);
        const response = await getProdutos({
          busca: termo,
          page: 1,
          page_size: 8,
          include_variations: true,
        });
        setSugestoesProdutos(extrairListaProdutos(response.data));
      } catch (error) {
        console.error("Erro ao buscar produtos para autocomplete:", error);
        setSugestoesProdutos([]);
      } finally {
        setLoadingBuscaProduto(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [buscaProduto, produtoSelecionado]);

  useEffect(() => {
    void carregarMovimentacoes(filtrosAplicados, paginaMovimentacoes);
  }, [carregarMovimentacoes, filtrosAplicados, paginaMovimentacoes]);

  useEffect(() => {
    if (!produtoAtivoId) {
      setDadosProduto(null);
      return;
    }

    void carregarResumoProduto(filtrosAplicados, paginaHistoricoVendas);
  }, [carregarResumoProduto, filtrosAplicados, paginaHistoricoVendas, produtoAtivoId]);

  useEffect(() => {
    const handleClickFora = (event) => {
      if (!buscaRef.current?.contains(event.target)) {
        setDropdownAberto(false);
      }
    };

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  const aplicarFiltros = useCallback(
    (event) => {
      if (event) event.preventDefault();

      const novosFiltros = {
        ...filtrosForm,
        page_size: Number(filtrosForm.page_size) || ITENS_POR_PAGINA_INICIAL,
        produto_id: produtoSelecionado?.id ? String(produtoSelecionado.id) : "",
      };

      setPaginaMovimentacoes(1);
      setPaginaHistoricoVendas(1);
      setFiltrosAplicados(novosFiltros);
    },
    [filtrosForm, produtoSelecionado],
  );

  const atualizarFiltro = useCallback((campo, valor) => {
    setFiltrosForm((prev) => ({
      ...prev,
      [campo]: valor,
    }));
  }, []);

  const alterarDataPersonalizada = useCallback(
    (campo, valor) => {
      setPeriodoSelecionado("personalizado");
      atualizarFiltro(campo, valor);
    },
    [atualizarFiltro],
  );

  const handlePeriodoChange = useCallback(
    (periodo) => {
      setPeriodoSelecionado(periodo.value);

      if (!periodo.dias) return;

      const proximosFiltros = {
        ...filtrosForm,
        data_inicio: dataInicioPorDias(periodo.dias),
        data_fim: hojeIso(),
      };

      setFiltrosForm(proximosFiltros);
      setPaginaMovimentacoes(1);
      setPaginaHistoricoVendas(1);
      setFiltrosAplicados({
        ...proximosFiltros,
        page_size: Number(proximosFiltros.page_size) || ITENS_POR_PAGINA_INICIAL,
        produto_id: produtoSelecionado?.id ? String(produtoSelecionado.id) : "",
      });
    },
    [filtrosForm, produtoSelecionado],
  );

  const selecionarProduto = useCallback((produto) => {
    setProdutoSelecionado(produto);
    setBuscaProduto("");
    setDropdownAberto(false);
    setSugestoesProdutos([]);
    setPaginaMovimentacoes(1);
    setPaginaHistoricoVendas(1);

    setFiltrosForm((prev) => ({
      ...prev,
      produto_id: String(produto.id),
    }));

    setFiltrosAplicados((prev) => ({
      ...prev,
      produto_id: String(produto.id),
    }));
  }, []);

  const limparProduto = useCallback(() => {
    setProdutoSelecionado(null);
    setBuscaProduto("");
    setSugestoesProdutos([]);
    setDropdownAberto(false);
    setPaginaMovimentacoes(1);
    setPaginaHistoricoVendas(1);
    setDadosProduto(null);

    setFiltrosForm((prev) => ({
      ...prev,
      produto_id: "",
    }));

    setFiltrosAplicados((prev) => ({
      ...prev,
      produto_id: "",
    }));
  }, []);

  const limparFiltros = useCallback(() => {
    const filtrosLimpos = criarFiltrosPadrao();

    setPeriodoSelecionado("30dias");
    setProdutoSelecionado(null);
    setBuscaProduto("");
    setSugestoesProdutos([]);
    setDropdownAberto(false);
    setPaginaMovimentacoes(1);
    setPaginaHistoricoVendas(1);
    setFiltrosForm(filtrosLimpos);
    setFiltrosAplicados(filtrosLimpos);
    setDadosProduto(null);
  }, []);

  const alterarBuscaProduto = useCallback((valor) => {
    setBuscaProduto(valor);
    setDropdownAberto(true);
  }, []);

  const limparBuscaProduto = useCallback(() => {
    setBuscaProduto("");
    setSugestoesProdutos([]);
  }, []);

  const exportarCsv = useCallback(async () => {
    try {
      setExportando(true);
      const response = await getRelatorioMovimentacoes(
        montarParamsMovimentacoes(filtrosAplicados, 1, { export_all: true }),
      );
      const linhas = Array.isArray(response?.data?.movimentacoes)
        ? response.data.movimentacoes
        : [];

      if (linhas.length === 0) {
        toast("Nao ha movimentacoes para exportar com o filtro atual.");
        return;
      }

      const cabecalho = [
        "Data",
        "Lancamento",
        "Produto",
        "Codigo",
        "SKU",
        "Tipo",
        "Motivo",
        "Entrada",
        "Saida",
        "Estoque",
        "Valor total",
        "Preco promocional",
        "Origem promocao",
        "Usuario",
        "Documento",
      ];

      const conteudo = [
        cabecalho.join(";"),
        ...linhas.map((mov) =>
          [
            mov.data || "",
            mov.lancamento || "",
            mov.produto_nome || "",
            mov.codigo || "",
            mov.sku || "",
            mov.tipo || "",
            mov.motivo_label || "",
            mov.entrada ?? "",
            mov.saida ?? "",
            mov.estoque ?? "",
            mov.valor_total ?? "",
            mov.em_promocao ? "Sim" : "Nao",
            mov.promocao_origem || "",
            mov.usuario || "",
            mov.numero_pedido || "",
          ].join(";"),
        ),
      ].join("\n");

      const blob = new Blob([conteudo], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `movimentacoes_produtos_${hojeIso()}.csv`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (error) {
      console.error("Erro ao exportar CSV:", error);
      toast.error(
        error?.response?.data?.detail || "Nao foi possivel exportar o CSV do filtro atual.",
      );
    } finally {
      setExportando(false);
    }
  }, [filtrosAplicados]);

  const janelasOrdenadas = useMemo(
    () => (Array.isArray(dadosProduto?.janelas) ? dadosProduto.janelas : []),
    [dadosProduto],
  );

  const curva30Dias = useMemo(
    () => (Array.isArray(dadosProduto?.curva_30_dias) ? dadosProduto.curva_30_dias : []),
    [dadosProduto],
  );

  const paginaAtualMovimentacoes = dadosMovimentacoes.page || paginaMovimentacoes;
  const totalPaginasMovimentacoes = dadosMovimentacoes.pages || 0;
  const totalPaginasHistorico = dadosProduto?.historico_pages || 0;
  const inicioItemMovimentacoes =
    dadosMovimentacoes.total_registros === 0
      ? 0
      : (paginaAtualMovimentacoes - 1) * dadosMovimentacoes.page_size + 1;
  const fimItemMovimentacoes =
    dadosMovimentacoes.total_registros === 0
      ? 0
      : Math.min(
          paginaAtualMovimentacoes * dadosMovimentacoes.page_size,
          dadosMovimentacoes.total_registros,
        );

  return {
    buscaRef,
    periodoSelecionado,
    filtrosForm,
    produtoSelecionado,
    buscaProduto,
    sugestoesProdutos,
    dropdownAberto,
    loadingBuscaProduto,
    loadingMovimentacoes,
    loadingResumoProduto,
    exportando,
    dadosMovimentacoes,
    dadosProduto,
    periodoAtivoDias,
    janelasOrdenadas,
    curva30Dias,
    paginaAtualMovimentacoes,
    totalPaginasMovimentacoes,
    totalPaginasHistorico,
    inicioItemMovimentacoes,
    fimItemMovimentacoes,
    aplicarFiltros,
    atualizarFiltro,
    alterarDataInicio: (valor) => alterarDataPersonalizada("data_inicio", valor),
    alterarDataFim: (valor) => alterarDataPersonalizada("data_fim", valor),
    handlePeriodoChange,
    selecionarProduto,
    limparProduto,
    limparFiltros,
    alterarBuscaProduto,
    focarBuscaProduto: () => setDropdownAberto(true),
    limparBuscaProduto,
    exportarCsv,
    setPaginaMovimentacoes,
    setPaginaHistoricoVendas,
    voltarParaProdutos: () => navigate("/produtos"),
    editarProdutoSelecionado: () => navigate(`/produtos/${produtoSelecionado.id}/editar`),
  };
}
