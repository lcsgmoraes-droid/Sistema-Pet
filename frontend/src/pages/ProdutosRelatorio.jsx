import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import {
  formatarMoeda,
  getProdutos,
  getRelatorioMovimentacoes,
  getRelatorioProdutoVendas,
} from "../api/produtos";

const ITENS_POR_PAGINA_INICIAL = 20;
const ITENS_HISTORICO_VENDAS = 10;

const PERIODOS = [
  { value: "7dias", label: "7 dias", dias: 7 },
  { value: "15dias", label: "15 dias", dias: 15 },
  { value: "30dias", label: "30 dias", dias: 30 },
  { value: "60dias", label: "60 dias", dias: 60 },
  { value: "90dias", label: "90 dias", dias: 90 },
  { value: "personalizado", label: "Personalizado", dias: null },
];

const formatarQuantidade = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor || 0));

const formatarData = (valor) => {
  if (!valor) return "-";
  return new Date(valor).toLocaleDateString("pt-BR");
};

const formatarDataHora = (valor) => {
  if (!valor) return "-";
  return new Date(valor).toLocaleString("pt-BR");
};

const formatarDiaCurto = (valor) =>
  new Date(valor).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });

function hojeIso() {
  return new Date().toISOString().split("T")[0];
}

function dataInicioPorDias(dias) {
  const data = new Date();
  data.setHours(0, 0, 0, 0);
  data.setDate(data.getDate() - Math.max(dias - 1, 0));
  return data.toISOString().split("T")[0];
}

function extrairListaProdutos(payload) {
  if (!payload) return [];
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.itens)) return payload.itens;
  if (Array.isArray(payload.produtos)) return payload.produtos;
  if (Array.isArray(payload.data)) return payload.data;
  if (Array.isArray(payload)) return payload;
  return [];
}

function ResumoCard({ titulo, valor, descricao, destaque = "blue" }) {
  const estilos = {
    blue: "border-blue-100 bg-blue-50 text-blue-900",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-900",
    amber: "border-amber-100 bg-amber-50 text-amber-900",
    rose: "border-rose-100 bg-rose-50 text-rose-900",
    violet: "border-violet-100 bg-violet-50 text-violet-900",
    slate: "border-slate-200 bg-slate-50 text-slate-900",
  };

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${estilos[destaque] || estilos.blue}`}>
      <p className="text-sm font-medium opacity-80">{titulo}</p>
      <p className="mt-2 text-2xl font-bold">{valor}</p>
      <p className="mt-2 text-xs opacity-75">{descricao}</p>
    </div>
  );
}

function JanelaVendaCard({ janela, ativa }) {
  return (
    <div
      className={`rounded-2xl border p-4 shadow-sm transition-colors ${
        ativa
          ? "border-blue-300 bg-blue-50"
          : "border-gray-200 bg-white"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-900">
            Ultimos {janela.dias} dias
          </p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {formatarQuantidade(janela.quantidade_vendida)}
          </p>
          <p className="mt-1 text-xs font-medium uppercase tracking-wide text-gray-500">
            unidades vendidas
          </p>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
            ativa ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"
          }`}
        >
          {janela.numero_vendas} vendas
        </span>
      </div>
      <div className="mt-3 space-y-1 text-xs text-gray-600">
        <p>Media/dia: {formatarQuantidade(janela.media_diaria)}</p>
        <p>Valor vendido: {formatarMoeda(janela.valor_vendido)}</p>
      </div>
    </div>
  );
}

function CurvaVendas30Dias({ pontos }) {
  const maximo = Math.max(...pontos.map((ponto) => Number(ponto.quantidade || 0)), 1);

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-gray-900">
            Ritmo de vendas nos ultimos 30 dias
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            Ajuda a enxergar picos, dias sem giro e o padrao real do item.
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
          Janela curta para compra
        </span>
      </div>

      <div className="mt-5 flex h-32 items-end gap-1.5">
        {pontos.map((ponto, index) => {
          const quantidade = Number(ponto.quantidade || 0);
          const altura = quantidade <= 0 ? 8 : Math.max((quantidade / maximo) * 100, 10);
          const destacar = index >= pontos.length - 7;

          return (
            <div key={ponto.data} className="group flex flex-1 flex-col items-center justify-end">
              <div
                className={`w-full rounded-t-md transition-all ${
                  destacar ? "bg-blue-500" : "bg-slate-300"
                }`}
                style={{ height: `${altura}%` }}
                title={`${formatarDiaCurto(ponto.data)} - ${formatarQuantidade(quantidade)} un`}
              />
              <span className="mt-2 text-[10px] text-gray-500 group-hover:text-gray-700">
                {index % 5 === 0 || index === pontos.length - 1 ? formatarDiaCurto(ponto.data) : ""}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function ProdutosRelatorio() {
  const navigate = useNavigate();
  const buscaRef = useRef(null);
  const [periodoSelecionado, setPeriodoSelecionado] = useState("30dias");
  const [filtrosForm, setFiltrosForm] = useState({
    data_inicio: dataInicioPorDias(30),
    data_fim: hojeIso(),
    tipo_movimentacao: "",
    page_size: ITENS_POR_PAGINA_INICIAL,
    produto_id: "",
  });
  const [filtrosAplicados, setFiltrosAplicados] = useState({
    data_inicio: dataInicioPorDias(30),
    data_fim: hojeIso(),
    tipo_movimentacao: "",
    page_size: ITENS_POR_PAGINA_INICIAL,
    produto_id: "",
  });
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
  const [dadosMovimentacoes, setDadosMovimentacoes] = useState({
    movimentacoes: [],
    total_registros: 0,
    page: 1,
    page_size: ITENS_POR_PAGINA_INICIAL,
    pages: 0,
    totais: {
      total_entradas: 0,
      total_saidas: 0,
      valor_total: 0,
    },
  });
  const [dadosProduto, setDadosProduto] = useState(null);

  const produtoAtivoId = filtrosAplicados.produto_id || "";
  const periodoAtivoDias = useMemo(
    () => PERIODOS.find((periodo) => periodo.value === periodoSelecionado)?.dias,
    [periodoSelecionado],
  );

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
  }, [filtrosAplicados, paginaMovimentacoes]);

  useEffect(() => {
    if (!produtoAtivoId) {
      setDadosProduto(null);
      return;
    }

    void carregarResumoProduto(filtrosAplicados, paginaHistoricoVendas);
  }, [filtrosAplicados, paginaHistoricoVendas, produtoAtivoId]);

  useEffect(() => {
    const handleClickFora = (event) => {
      if (!buscaRef.current?.contains(event.target)) {
        setDropdownAberto(false);
      }
    };

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  const montarParamsMovimentacoes = (filtros, pagina, extra = {}) => {
    const params = {
      page: pagina,
      page_size: Number(filtros.page_size) || ITENS_POR_PAGINA_INICIAL,
      ...extra,
    };

    if (filtros.data_inicio) params.data_inicio = filtros.data_inicio;
    if (filtros.data_fim) params.data_fim = filtros.data_fim;
    if (filtros.tipo_movimentacao) params.tipo_movimentacao = filtros.tipo_movimentacao;
    if (filtros.produto_id) params.produto_id = filtros.produto_id;

    return params;
  };

  const carregarMovimentacoes = async (filtros, pagina) => {
    try {
      setLoadingMovimentacoes(true);
      const response = await getRelatorioMovimentacoes(
        montarParamsMovimentacoes(filtros, pagina),
      );
      const payload = response?.data || {};
      setDadosMovimentacoes({
        movimentacoes: Array.isArray(payload.movimentacoes) ? payload.movimentacoes : [],
        total_registros: Number(payload.total_registros || 0),
        page: Number(payload.page || pagina),
        page_size: Number(payload.page_size || filtros.page_size || ITENS_POR_PAGINA_INICIAL),
        pages: Number(payload.pages || 0),
        totais: {
          total_entradas: Number(payload?.totais?.total_entradas || 0),
          total_saidas: Number(payload?.totais?.total_saidas || 0),
          valor_total: Number(payload?.totais?.valor_total || 0),
        },
      });
    } catch (error) {
      console.error("Erro ao carregar movimentacoes:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel carregar as movimentacoes.",
      );
      setDadosMovimentacoes({
        movimentacoes: [],
        total_registros: 0,
        page: 1,
        page_size: Number(filtros.page_size || ITENS_POR_PAGINA_INICIAL),
        pages: 0,
        totais: {
          total_entradas: 0,
          total_saidas: 0,
          valor_total: 0,
        },
      });
    } finally {
      setLoadingMovimentacoes(false);
    }
  };

  const carregarResumoProduto = async (filtros, pagina) => {
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
        error?.response?.data?.detail ||
          "Nao foi possivel carregar o historico do produto.",
      );
      setDadosProduto(null);
    } finally {
      setLoadingResumoProduto(false);
    }
  };

  const aplicarFiltros = (event) => {
    if (event) event.preventDefault();

    const novosFiltros = {
      ...filtrosForm,
      page_size: Number(filtrosForm.page_size) || ITENS_POR_PAGINA_INICIAL,
      produto_id: produtoSelecionado?.id ? String(produtoSelecionado.id) : "",
    };

    setPaginaMovimentacoes(1);
    setPaginaHistoricoVendas(1);
    setFiltrosAplicados(novosFiltros);
  };

  const atualizarFiltro = (campo, valor) => {
    setFiltrosForm((prev) => ({
      ...prev,
      [campo]: valor,
    }));
  };

  const handlePeriodoChange = (periodo) => {
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
  };

  const selecionarProduto = (produto) => {
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
  };

  const limparProduto = () => {
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
  };

  const limparFiltros = () => {
    const filtrosLimpos = {
      data_inicio: dataInicioPorDias(30),
      data_fim: hojeIso(),
      tipo_movimentacao: "",
      page_size: ITENS_POR_PAGINA_INICIAL,
      produto_id: "",
    };

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
  };

  const exportarCsv = async () => {
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
        "Usuario",
        "Documento",
      ];

      const conteudo = [
        cabecalho.join(";"),
        ...linhas.map((mov) => [
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
          mov.usuario || "",
          mov.numero_pedido || "",
        ].join(";")),
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
        error?.response?.data?.detail ||
          "Nao foi possivel exportar o CSV do filtro atual.",
      );
    } finally {
      setExportando(false);
    }
  };

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

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Giro de Produto e Movimentacoes
          </h1>
          <p className="mt-2 max-w-4xl text-sm text-gray-600">
            Use esta tela para decidir compra com base no giro real do item.
            Ao escolher um produto, o painel mostra vendas em 7, 15, 30, 60 e
            90 dias, historico recente e as movimentacoes de estoque com
            paginacao leve.
          </p>
        </div>

        <button
          onClick={() => navigate("/produtos")}
          className="inline-flex items-center justify-center rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
        >
          Voltar para produtos
        </button>
      </div>

      <form
        onSubmit={aplicarFiltros}
        className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm"
      >
        <div className="flex flex-wrap gap-2">
          {PERIODOS.map((periodo) => (
            <button
              key={periodo.value}
              type="button"
              onClick={() => handlePeriodoChange(periodo)}
              className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                periodoSelecionado === periodo.value
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {periodo.label}
            </button>
          ))}
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Data inicio
            </label>
            <input
              type="date"
              value={filtrosForm.data_inicio}
              onChange={(event) => {
                setPeriodoSelecionado("personalizado");
                atualizarFiltro("data_inicio", event.target.value);
              }}
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Data fim
            </label>
            <input
              type="date"
              value={filtrosForm.data_fim}
              onChange={(event) => {
                setPeriodoSelecionado("personalizado");
                atualizarFiltro("data_fim", event.target.value);
              }}
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div className="relative md:col-span-2" ref={buscaRef}>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Produto
            </label>
            {produtoSelecionado ? (
              <div className="flex min-h-[46px] items-center gap-3 rounded-xl border border-blue-300 bg-blue-50 px-3 py-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-gray-900">
                    {produtoSelecionado.nome}
                  </p>
                  <p className="truncate text-xs text-gray-600">
                    {[produtoSelecionado.codigo, produtoSelecionado.sku, produtoSelecionado.codigo_barras]
                      .filter(Boolean)
                      .join(" | ")}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={limparProduto}
                  className="rounded-lg px-2 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-50"
                >
                  Limpar
                </button>
              </div>
            ) : (
              <div className="relative">
                <input
                  type="text"
                  value={buscaProduto}
                  onChange={(event) => {
                    setBuscaProduto(event.target.value);
                    setDropdownAberto(true);
                  }}
                  onFocus={() => setDropdownAberto(true)}
                  placeholder="Buscar por nome, codigo, SKU ou codigo de barras"
                  className="w-full rounded-xl border border-gray-300 px-3 py-2.5 pr-10 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
                {buscaProduto && (
                  <button
                    type="button"
                    onClick={() => {
                      setBuscaProduto("");
                      setSugestoesProdutos([]);
                    }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 transition-colors hover:text-red-500"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
                {dropdownAberto && (buscaProduto.trim().length >= 2 || loadingBuscaProduto) && (
                  <div className="absolute left-0 right-0 top-full z-20 mt-2 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-xl">
                    {loadingBuscaProduto ? (
                      <div className="px-4 py-3 text-sm text-gray-500">
                        Buscando produtos...
                      </div>
                    ) : sugestoesProdutos.length === 0 ? (
                      <div className="px-4 py-3 text-sm text-gray-500">
                        Nenhum produto encontrado para esse termo.
                      </div>
                    ) : (
                      sugestoesProdutos.map((produto) => (
                        <button
                          key={produto.id}
                          type="button"
                          onMouseDown={() => selecionarProduto(produto)}
                          className="flex w-full items-start justify-between gap-3 border-b border-gray-100 px-4 py-3 text-left transition-colors hover:bg-blue-50 last:border-b-0"
                        >
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold text-gray-900">
                              {produto.nome}
                            </p>
                            <p className="truncate text-xs text-gray-500">
                              {[produto.codigo, produto.sku, produto.codigo_barras]
                                .filter(Boolean)
                                .join(" | ")}
                            </p>
                          </div>
                          <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-700">
                            Estoque {formatarQuantidade(produto.estoque_atual)}
                          </span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Tipo da movimentacao
            </label>
            <select
              value={filtrosForm.tipo_movimentacao}
              onChange={(event) => atualizarFiltro("tipo_movimentacao", event.target.value)}
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">Todos os tipos</option>
              <option value="entrada">Entrada</option>
              <option value="saida">Saida</option>
              <option value="transferencia">Transferencia</option>
            </select>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">Itens por pagina</label>
            <select
              value={filtrosForm.page_size}
              onChange={(event) => atualizarFiltro("page_size", Number(event.target.value))}
              className="rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              {[20, 50, 100].map((opcao) => (
                <option key={opcao} value={opcao}>
                  {opcao}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={limparFiltros}
              className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Limpar filtros
            </button>
            <button
              type="submit"
              className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              Atualizar painel
            </button>
          </div>
        </div>
      </form>

      {produtoSelecionado ? (
        <div className="space-y-6">
          <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-2xl font-bold text-gray-900">
                    {dadosProduto?.produto?.nome || produtoSelecionado.nome}
                  </h2>
                  {dadosProduto?.produto?.categoria_nome && (
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                      {dadosProduto.produto.categoria_nome}
                    </span>
                  )}
                  {dadosProduto?.produto?.marca_nome && (
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                      {dadosProduto.produto.marca_nome}
                    </span>
                  )}
                </div>
                <p className="mt-2 text-sm text-gray-600">
                  {[dadosProduto?.produto?.codigo, dadosProduto?.produto?.sku, dadosProduto?.produto?.codigo_barras]
                    .filter(Boolean)
                    .join(" | ") || "Sem codigo complementar"}
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => navigate(`/produtos/${produtoSelecionado.id}/editar`)}
                  className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
                >
                  Editar produto
                </button>
                <button
                  type="button"
                  onClick={exportarCsv}
                  disabled={exportando}
                  className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {exportando ? "Exportando..." : "Exportar movimentacoes"}
                </button>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <ResumoCard
                titulo="Estoque atual"
                valor={formatarQuantidade(dadosProduto?.produto?.estoque_atual)}
                descricao={`Minimo: ${formatarQuantidade(dadosProduto?.produto?.estoque_minimo)}`}
                destaque="blue"
              />
              <ResumoCard
                titulo="Cobertura estimada"
                valor={
                  dadosProduto?.resumo?.cobertura_estimada_dias != null
                    ? `${formatarQuantidade(dadosProduto.resumo.cobertura_estimada_dias)} dias`
                    : "Sem base"
                }
                descricao="Calculado pela media diaria dos ultimos 30 dias."
                destaque="amber"
              />
              <ResumoCard
                titulo="Media diaria 30 dias"
                valor={formatarQuantidade(dadosProduto?.resumo?.media_diaria_30)}
                descricao={`Vendidos 30 dias: ${formatarQuantidade(dadosProduto?.resumo?.quantidade_vendida_30)}`}
                destaque="emerald"
              />
              <ResumoCard
                titulo="Ultima venda"
                valor={formatarData(dadosProduto?.resumo?.ultima_venda?.data_venda)}
                descricao={
                  dadosProduto?.resumo?.dias_sem_vender != null
                    ? `${dadosProduto.resumo.dias_sem_vender} dia(s) sem vender`
                    : "Sem historico de venda"
                }
                destaque="violet"
              />
            </div>
          </div>

          {loadingResumoProduto ? (
            <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-500 shadow-sm">
              Carregando historico comercial do produto...
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
                {janelasOrdenadas.map((janela) => (
                  <JanelaVendaCard
                    key={janela.dias}
                    janela={janela}
                    ativa={periodoAtivoDias === janela.dias}
                  />
                ))}
              </div>

              {curva30Dias.length > 0 && <CurvaVendas30Dias pontos={curva30Dias} />}

              <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
                <div className="flex flex-col gap-3 border-b border-gray-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      Historico recente de vendas do produto
                    </h3>
                    <p className="mt-1 text-sm text-gray-600">
                      Veja quando vendeu, para quem e em qual quantidade dentro do periodo selecionado.
                    </p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                    {dadosProduto?.historico_total || 0} registro(s)
                  </span>
                </div>

                {(dadosProduto?.historico_vendas || []).length === 0 ? (
                  <div className="px-5 py-8 text-center text-sm text-gray-500">
                    Nenhuma venda do produto encontrada neste recorte.
                  </div>
                ) : (
                  <>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                              Data
                            </th>
                            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                              Venda
                            </th>
                            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                              Cliente
                            </th>
                            <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                              Qtd
                            </th>
                            <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                              Preco unit
                            </th>
                            <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                              Total
                            </th>
                            <th className="px-5 py-3 text-center text-xs font-semibold uppercase tracking-wide text-gray-500">
                              Status
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 bg-white">
                          {dadosProduto.historico_vendas.map((item) => (
                            <tr key={item.id} className="hover:bg-gray-50">
                              <td className="px-5 py-3 text-sm text-gray-700">
                                {formatarData(item.data_venda)}
                              </td>
                              <td className="px-5 py-3 text-sm font-medium text-gray-900">
                                {item.numero_venda || "-"}
                              </td>
                              <td className="px-5 py-3 text-sm text-gray-700">
                                {item.cliente_nome || "Sem cliente"}
                              </td>
                              <td className="px-5 py-3 text-right text-sm font-semibold text-gray-900">
                                {formatarQuantidade(item.quantidade)}
                              </td>
                              <td className="px-5 py-3 text-right text-sm text-gray-700">
                                {formatarMoeda(item.preco_unitario)}
                              </td>
                              <td className="px-5 py-3 text-right text-sm font-semibold text-gray-900">
                                {formatarMoeda(item.subtotal)}
                              </td>
                              <td className="px-5 py-3 text-center">
                                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                                  {item.status || "-"}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="flex flex-col gap-3 border-t border-gray-200 px-5 py-4 md:flex-row md:items-center md:justify-between">
                      <p className="text-sm text-gray-600">
                        Pagina {dadosProduto?.historico_page || 1} de {totalPaginasHistorico || 1}
                      </p>
                      <div className="flex gap-3">
                        <button
                          type="button"
                          onClick={() => setPaginaHistoricoVendas((prev) => Math.max(prev - 1, 1))}
                          disabled={(dadosProduto?.historico_page || 1) <= 1}
                          className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Anterior
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            setPaginaHistoricoVendas((prev) =>
                              totalPaginasHistorico > 0 ? Math.min(prev + 1, totalPaginasHistorico) : prev,
                            )
                          }
                          disabled={
                            totalPaginasHistorico === 0 ||
                            (dadosProduto?.historico_page || 1) >= totalPaginasHistorico
                          }
                          className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Proxima
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="rounded-3xl border border-dashed border-blue-200 bg-blue-50 p-8 text-center shadow-sm">
          <h2 className="text-xl font-semibold text-blue-900">
            Selecione um produto para enxergar o padrao de venda
          </h2>
          <p className="mx-auto mt-3 max-w-3xl text-sm text-blue-800">
            O objetivo principal desta tela agora e apoiar a compra. Busque o item por nome, SKU, codigo ou codigo de barras para ver o giro nos ultimos 7, 15, 30, 60 e 90 dias, alem do historico recente de vendas.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <ResumoCard
          titulo="Total de entradas"
          valor={formatarQuantidade(dadosMovimentacoes.totais.total_entradas)}
          descricao="Somatorio de entradas dentro do filtro atual."
          destaque="emerald"
        />
        <ResumoCard
          titulo="Total de saidas"
          valor={formatarQuantidade(dadosMovimentacoes.totais.total_saidas)}
          descricao="Somatorio de saidas dentro do filtro atual."
          destaque="rose"
        />
        <ResumoCard
          titulo="Valor movimentado"
          valor={formatarMoeda(dadosMovimentacoes.totais.valor_total)}
          descricao="Baseado no valor total das movimentacoes filtradas."
          destaque="blue"
        />
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-gray-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Movimentacoes filtradas
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              Historico operacional paginado para manter a tela leve mesmo com muitos registros.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
              Exibindo {inicioItemMovimentacoes}-{fimItemMovimentacoes} de {dadosMovimentacoes.total_registros}
            </span>
            <button
              type="button"
              onClick={exportarCsv}
              disabled={exportando || dadosMovimentacoes.total_registros === 0}
              className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {exportando ? "Exportando..." : "Exportar CSV"}
            </button>
          </div>
        </div>

        {loadingMovimentacoes ? (
          <div className="px-5 py-8 text-center text-sm text-gray-500">
            Carregando movimentacoes...
          </div>
        ) : dadosMovimentacoes.movimentacoes.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-gray-500">
            Nenhuma movimentacao encontrada com o filtro atual.
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Lancamento
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Produto
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Tipo / motivo
                    </th>
                    <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Entrada
                    </th>
                    <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Saida
                    </th>
                    <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Estoque apos
                    </th>
                    <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Valor
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Usuario
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {dadosMovimentacoes.movimentacoes.map((mov) => {
                    const tipoLower = String(mov.tipo || "").toLowerCase();
                    const badgeClasse =
                      tipoLower === "entrada"
                        ? "bg-emerald-100 text-emerald-700"
                        : tipoLower === "transferencia"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-rose-100 text-rose-700";

                    return (
                      <tr key={mov.id} className="hover:bg-gray-50">
                        <td className="px-5 py-3 text-sm text-gray-700">
                          <p className="font-medium text-gray-900">
                            {formatarDataHora(mov.data_completa)}
                          </p>
                          <p className="text-xs text-gray-500">
                            {mov.numero_pedido || "Sem documento"}
                          </p>
                        </td>
                        <td className="px-5 py-3 text-sm text-gray-700">
                          <p className="font-semibold text-gray-900">
                            {mov.produto_nome || "-"}
                          </p>
                          <p className="text-xs text-gray-500">
                            {[mov.codigo, mov.sku, mov.codigo_barras].filter(Boolean).join(" | ") || "Sem codigo"}
                          </p>
                        </td>
                        <td className="px-5 py-3 text-sm text-gray-700">
                          <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${badgeClasse}`}>
                            {mov.tipo || "-"}
                          </span>
                          <p className="mt-2 text-xs text-gray-500">
                            {mov.motivo_label || "Sem motivo informado"}
                          </p>
                        </td>
                        <td className="px-5 py-3 text-right text-sm font-semibold text-emerald-700">
                          {mov.entrada != null ? formatarQuantidade(mov.entrada) : "-"}
                        </td>
                        <td className="px-5 py-3 text-right text-sm font-semibold text-rose-700">
                          {mov.saida != null ? formatarQuantidade(mov.saida) : "-"}
                        </td>
                        <td className="px-5 py-3 text-right text-sm font-medium text-gray-900">
                          {formatarQuantidade(mov.estoque)}
                        </td>
                        <td className="px-5 py-3 text-right text-sm font-medium text-gray-900">
                          {formatarMoeda(mov.valor_total)}
                        </td>
                        <td className="px-5 py-3 text-sm text-gray-700">
                          {mov.usuario || "-"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="flex flex-col gap-3 border-t border-gray-200 px-5 py-4 md:flex-row md:items-center md:justify-between">
              <p className="text-sm text-gray-600">
                Pagina {paginaAtualMovimentacoes} de {totalPaginasMovimentacoes || 1}
              </p>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setPaginaMovimentacoes((prev) => Math.max(prev - 1, 1))}
                  disabled={paginaAtualMovimentacoes <= 1}
                  className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Anterior
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setPaginaMovimentacoes((prev) =>
                      totalPaginasMovimentacoes > 0
                        ? Math.min(prev + 1, totalPaginasMovimentacoes)
                        : prev,
                    )
                  }
                  disabled={
                    totalPaginasMovimentacoes === 0 ||
                    paginaAtualMovimentacoes >= totalPaginasMovimentacoes
                  }
                  className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Proxima
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
