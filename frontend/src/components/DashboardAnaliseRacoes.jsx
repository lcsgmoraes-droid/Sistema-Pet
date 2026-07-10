import { useState, useEffect } from "react";
import { TrendingUp, BarChart3, Package, RefreshCw, Target, ShoppingCart } from "lucide-react";
import { toast } from "react-hot-toast";
import api from "../api";
import DashboardRacoesAnaliseSegmento from "./racoes/DashboardRacoesAnaliseSegmento";
import DashboardRacoesComparacaoDetalhada from "./racoes/DashboardRacoesComparacaoDetalhada";
import DashboardRacoesComparacaoMarcas from "./racoes/DashboardRacoesComparacaoMarcas";
import DashboardRacoesFiltros from "./racoes/DashboardRacoesFiltros";
import DashboardRacoesRankingVendas from "./racoes/DashboardRacoesRankingVendas";
import DashboardRacoesResumoCards from "./racoes/DashboardRacoesResumoCards";
import { calcularMargem, calcularROI } from "./racoes/dashboardRacoesComparacaoUtils";

/**
 * Dashboard de Análise Dinâmica de Rações - Fase 4
 *
 * Features:
 * - Filtros dinâmicos (porte, fase, sabor, marca)
 * - Gráficos de margem por segmento
 * - Comparação de preços entre marcas
 * - Ranking de produtos mais vendidos
 *
 * @version 1.0.0 (2026-02-14)
 */
const DashboardAnaliseRacoes = () => {
  // ============================================================================
  // STATES
  // ============================================================================

  const [loading, setLoading] = useState(true);
  const [loadingAnalise, setLoadingAnalise] = useState(false);

  // Resumo geral
  const [resumo, setResumo] = useState(null);

  // Análises
  const [analiseSegmento, setAnaliseSegmento] = useState([]);
  const [comparacaoMarcas, setComparacaoMarcas] = useState([]);
  const [rankingVendas, setRankingVendas] = useState([]);
  const [produtosComparacao, setProdutosComparacao] = useState([]);
  const [ordenacao, setOrdenacao] = useState({ campo: null, direcao: "asc" });

  // Filtros
  const [filtros, setFiltros] = useState({
    especies: [],
    linhas: [],
    portes: [],
    fases: [],
    tratamentos: [],
    sabores: [],
    pesos: [],
    marca_ids: [],
    categoria_ids: [],
    margem_min: null,
    margem_max: null,
    data_inicio: null,
    data_fim: null,
  });

  // Opções de filtros (carregadas do backend)
  const [opcoesFiltros, setOpcoesFiltros] = useState({
    marcas: [],
    categorias: [],
    especies: [],
    linhas: [],
    portes: [],
    fases: [],
    tratamentos: [],
    sabores: [],
    pesos: [],
  });

  // Tipo de segmento para análise
  const [tipoSegmento, setTipoSegmento] = useState("porte");

  // Controle de exibição de filtros
  const [mostrarFiltros, setMostrarFiltros] = useState(true);

  // Abas ativas
  const [abaAtiva, setAbaAtiva] = useState("comparacao");

  // ============================================================================
  // EFFECTS
  // ============================================================================

  useEffect(() => {
    carregarDados();
  }, []);

  // ============================================================================
  // FUNÇÕES DE CARREGAMENTO
  // ============================================================================

  const carregarDados = async () => {
    try {
      setLoading(true);

      // 🔍 DEBUG: Verificar token antes da requisição
      console.log("🔐 [DashboardAnaliseRacoes] Iniciando carregamento de dados", {
      });

      // Carregar opções de filtros
      console.log("📡 [DashboardAnaliseRacoes] Chamando: /racoes/analises/opcoes-filtros");
      const resOpcoes = await api.get("/racoes/analises/opcoes-filtros");
      console.log("✅ [DashboardAnaliseRacoes] Opções carregadas:", resOpcoes.data);
      setOpcoesFiltros(resOpcoes.data);

      // Carregar resumo (sem filtros de data para overview geral)
      await carregarResumo();

      setLoading(false);
    } catch (error) {
      console.error("❌ [DashboardAnaliseRacoes] Erro ao carregar dados:", {
        message: error.message,
        status: error.response?.status,
      });

      if (error.response?.status === 403) {
        toast.error("Acesso negado. Verifique suas permissões ou faça login novamente.");
      } else {
        toast.error("Erro ao carregar dados do dashboard");
      }

      setLoading(false);
    }
  };

  const carregarResumo = async (dataInicio = null, dataFim = null) => {
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;

      const res = await api.get("/racoes/analises/resumo", { params });
      setResumo(res.data);
    } catch (error) {
      console.error("Erro ao carregar resumo:", error);
      toast.error("Erro ao carregar resumo");
    }
  };

  const carregarAnaliseSegmento = async () => {
    try {
      setLoadingAnalise(true);
      const res = await api.post(
        `/racoes/analises/margem-por-segmento?tipo_segmento=${tipoSegmento}`,
        filtros,
      );
      setAnaliseSegmento(res.data);
      setLoadingAnalise(false);
    } catch (error) {
      console.error("Erro ao carregar análise:", error);
      toast.error("Erro ao carregar análise de segmento");
      setLoadingAnalise(false);
    }
  };

  const carregarComparacaoMarcas = async () => {
    try {
      setLoadingAnalise(true);
      const res = await api.post("/racoes/analises/comparacao-marcas", filtros);
      setComparacaoMarcas(res.data);
      setLoadingAnalise(false);
    } catch (error) {
      console.error("Erro ao carregar comparação:", error);
      toast.error("Erro ao carregar comparação de marcas");
      setLoadingAnalise(false);
    }
  };

  const carregarRankingVendas = async () => {
    try {
      if (!filtros.data_inicio || !filtros.data_fim) {
        toast.error("Selecione um período para ver o ranking de vendas");
        return;
      }

      setLoadingAnalise(true);
      const res = await api.get("/racoes/analises/ranking-vendas", {
        params: {
          data_inicio: filtros.data_inicio,
          data_fim: filtros.data_fim,
          limite: 20,
        },
      });
      setRankingVendas(res.data);
      setLoadingAnalise(false);
    } catch (error) {
      console.error("Erro ao carregar ranking:", error);
      toast.error("Erro ao carregar ranking de vendas");
      setLoadingAnalise(false);
    }
  };

  const carregarProdutosComparacao = async () => {
    try {
      setLoadingAnalise(true);
      const res = await api.post("/racoes/analises/produtos-comparacao", filtros);
      setProdutosComparacao(res.data);
      setOrdenacao({ campo: null, direcao: "asc" }); // Reset ordenação
      setLoadingAnalise(false);
    } catch (error) {
      console.error("Erro ao carregar produtos para comparação:", error);
      toast.error("Erro ao carregar produtos");
      setLoadingAnalise(false);
    }
  };

  const ordenarProdutos = (campo) => {
    const novaDirecao = ordenacao.campo === campo && ordenacao.direcao === "asc" ? "desc" : "asc";
    setOrdenacao({ campo, direcao: novaDirecao });

    const produtosOrdenados = [...produtosComparacao].sort((a, b) => {
      let valorA, valorB;

      switch (campo) {
        case "nome":
          valorA = a.nome;
          valorB = b.nome;
          break;
        case "custo":
          valorA = a.preco_custo || 0;
          valorB = b.preco_custo || 0;
          break;
        case "venda":
          valorA = a.preco_venda || 0;
          valorB = b.preco_venda || 0;
          break;
        case "lucro":
          valorA = (a.preco_venda || 0) - (a.preco_custo || 0);
          valorB = (b.preco_venda || 0) - (b.preco_custo || 0);
          break;
        case "margem":
          valorA = calcularMargem(a.preco_custo, a.preco_venda);
          valorB = calcularMargem(b.preco_custo, b.preco_venda);
          break;
        case "roi":
          valorA = calcularROI(a.preco_custo, a.preco_venda);
          valorB = calcularROI(b.preco_custo, b.preco_venda);
          break;
        case "custokg":
          valorA = (a.preco_custo || 0) / (a.peso_embalagem || 1);
          valorB = (b.preco_custo || 0) / (b.peso_embalagem || 1);
          break;
        case "vendakg":
          valorA = (a.preco_venda || 0) / (a.peso_embalagem || 1);
          valorB = (b.preco_venda || 0) / (b.peso_embalagem || 1);
          break;
        default:
          return 0;
      }

      if (typeof valorA === "string") {
        return novaDirecao === "asc" ? valorA.localeCompare(valorB) : valorB.localeCompare(valorA);
      }

      return novaDirecao === "asc" ? valorA - valorB : valorB - valorA;
    });

    setProdutosComparacao(produtosOrdenados);
  };

  // ============================================================================
  // HANDLERS
  // ============================================================================

  const handleFiltroChange = (campo, valor) => {
    setFiltros((prev) => ({
      ...prev,
      [campo]: valor,
    }));
  };

  const toggleFiltroMultiplo = (campo, valor) => {
    setFiltros((prev) => {
      const atual = prev[campo] || [];
      const existe = atual.includes(valor);

      return {
        ...prev,
        [campo]: existe
          ? atual.filter((v) => v !== valor) // Remove
          : [...atual, valor], // Adiciona
      };
    });
  };

  const handleAplicarFiltros = () => {
    if (abaAtiva === "segmento") {
      carregarAnaliseSegmento();
    } else if (abaAtiva === "marcas") {
      carregarComparacaoMarcas();
    } else if (abaAtiva === "ranking") {
      carregarRankingVendas();
    } else if (abaAtiva === "comparacao") {
      carregarProdutosComparacao();
    }

    // Atualizar resumo com período se houver
    if (filtros.data_inicio && filtros.data_fim) {
      carregarResumo(filtros.data_inicio, filtros.data_fim);
    }
  };

  const handleLimparFiltros = () => {
    setFiltros({
      especies: [],
      linhas: [],
      portes: [],
      fases: [],
      tratamentos: [],
      sabores: [],
      pesos: [],
      marca_ids: [],
      categoria_ids: [],
      margem_min: null,
      margem_max: null,
      data_inicio: null,
      data_fim: null,
    });
  };

  const handleMudarAba = (aba) => {
    setAbaAtiva(aba);

    // Carregar dados da aba automaticamente
    if (aba === "segmento" && analiseSegmento.length === 0) {
      carregarAnaliseSegmento();
    } else if (aba === "marcas" && comparacaoMarcas.length === 0) {
      carregarComparacaoMarcas();
    } else if (aba === "ranking" && rankingVendas.length === 0) {
      if (filtros.data_inicio && filtros.data_fim) {
        carregarRankingVendas();
      }
    } else if (aba === "comparacao" && produtosComparacao.length === 0) {
      carregarProdutosComparacao();
    }
  };

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================

  // ============================================================================
  // RENDER PRINCIPAL
  // ============================================================================

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart3 className="h-7 w-7 text-blue-600" />
            Comparador de Rações
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Compare itens da mesma linha com foco em custo, margem, venda por kg e estoque.
          </p>
        </div>

        <button
          onClick={() => carregarDados()}
          className="px-4 py-2 bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Atualizar
        </button>
      </div>

      {/* Resumo */}
      <DashboardRacoesResumoCards resumo={resumo} />

      {/* Filtros */}
      <DashboardRacoesFiltros
        filtros={filtros}
        mostrarFiltros={mostrarFiltros}
        opcoesFiltros={opcoesFiltros}
        onAplicarFiltros={handleAplicarFiltros}
        onFiltroChange={handleFiltroChange}
        onLimparFiltros={handleLimparFiltros}
        onToggleFiltroMultiplo={toggleFiltroMultiplo}
        onToggleMostrarFiltros={() => setMostrarFiltros(!mostrarFiltros)}
      />

      {/* Abas */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="border-b border-gray-200">
          <div className="flex space-x-1 p-2 overflow-x-auto">
            <button
              onClick={() => handleMudarAba("comparacao")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                abaAtiva === "comparacao"
                  ? "bg-blue-600 text-white shadow-md"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <Target className="h-4 w-4 inline mr-2" />
              Comparação detalhada
            </button>

            <button
              onClick={() => handleMudarAba("segmento")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                abaAtiva === "segmento"
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <TrendingUp className="h-4 w-4 inline mr-2" />
              Margem por Segmento
            </button>

            <button
              onClick={() => handleMudarAba("marcas")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                abaAtiva === "marcas"
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <Package className="h-4 w-4 inline mr-2" />
              Comparação de Marcas
            </button>

            <button
              onClick={() => handleMudarAba("ranking")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                abaAtiva === "ranking"
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <ShoppingCart className="h-4 w-4 inline mr-2" />
              Ranking de Vendas
            </button>
          </div>
        </div>

        <div className="p-4">
          {abaAtiva === "comparacao" && (
            <DashboardRacoesComparacaoDetalhada
              loadingAnalise={loadingAnalise}
              produtosComparacao={produtosComparacao}
              ordenarProdutos={ordenarProdutos}
              ordenacao={ordenacao}
            />
          )}
          {abaAtiva === "resumo" && <DashboardRacoesResumoCards resumo={resumo} />}
          {abaAtiva === "segmento" && (
            <DashboardRacoesAnaliseSegmento
              analiseSegmento={analiseSegmento}
              loadingAnalise={loadingAnalise}
              tipoSegmento={tipoSegmento}
              onTipoSegmentoChange={(novoTipoSegmento) => {
                setTipoSegmento(novoTipoSegmento);
                setTimeout(() => carregarAnaliseSegmento(), 0);
              }}
            />
          )}
          {abaAtiva === "marcas" && (
            <DashboardRacoesComparacaoMarcas
              comparacaoMarcas={comparacaoMarcas}
              loadingAnalise={loadingAnalise}
            />
          )}
          {abaAtiva === "ranking" && (
            <DashboardRacoesRankingVendas
              rankingVendas={rankingVendas}
              loadingAnalise={loadingAnalise}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardAnaliseRacoes;
