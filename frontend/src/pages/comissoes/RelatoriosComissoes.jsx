import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api";
import RelatoriosComissoesSections from "./relatorios/RelatoriosComissoesSections";

/**
 * RELATÓRIOS ANALÍTICOS DE COMISSÕES
 * =====================================
 * Página de análise de rentabilidade e tomada de decisão.
 * NÃO recalcula comissões, apenas consulta dados existentes.
 */

const RelatoriosComissoes = () => {
  const navigate = useNavigate();

  // Estado
  const [abaAtiva, setAbaAtiva] = useState("margem-produto");
  const [carregando, setCarregando] = useState(false);

  // Filtros
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");

  // Dados dos relatórios
  const [dadosMargemProduto, setDadosMargemProduto] = useState(null);
  const [dadosProdutosPrejudiciais, setDadosProdutosPrejudiciais] = useState(null);
  const [dadosRankingFuncionarios, setDadosRankingFuncionarios] = useState(null);
  const [dadosRankingProdutos, setDadosRankingProdutos] = useState(null);
  const [dadosRankingCategorias, setDadosRankingCategorias] = useState(null);
  const [dadosDRE, setDadosDRE] = useState(null);

  // ========================================
  // CARREGAMENTO DE DADOS
  // ========================================

  const carregarRelatorio = async (tipo) => {
    setCarregando(true);
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;

      let endpoint = "";
      let setDados = null;

      switch (tipo) {
        case "margem-produto":
          endpoint = "/relatorios-comissoes/margem-produto";
          setDados = setDadosMargemProduto;
          break;
        case "produtos-prejudiciais":
          endpoint = "/relatorios-comissoes/produtos-prejudiciais";
          setDados = setDadosProdutosPrejudiciais;
          break;
        case "ranking-funcionarios":
          endpoint = "/relatorios-comissoes/ranking-funcionarios";
          setDados = setDadosRankingFuncionarios;
          break;
        case "ranking-produtos":
          endpoint = "/relatorios-comissoes/ranking-produtos";
          setDados = setDadosRankingProdutos;
          break;
        case "ranking-categorias":
          endpoint = "/relatorios-comissoes/ranking-categorias";
          setDados = setDadosRankingCategorias;
          break;
        case "dre":
          endpoint = "/relatorios-comissoes/visao-dre";
          params.ano = 2026;
          setDados = setDadosDRE;
          break;
        default:
          setCarregando(false);
          return;
      }

      const response = await api.get(endpoint, {
        params,
        timeout: 10000, // 10 segundos timeout
      });
      setDados(response.data);
    } catch (error) {
      console.error(`Erro ao carregar relatório ${tipo}:`, error);

      // Se for erro de rede/timeout, mostrar estrutura vazia
      if (error.code === "ECONNABORTED" || error.message.includes("timeout")) {
        alert("⏱️ Tempo de resposta excedido. Verifique se o backend está rodando.");
      } else {
        alert("❌ Erro ao carregar relatório. Verifique o console para detalhes.");
      }
    } finally {
      setCarregando(false);
    }
  };

  // Carregar relatório ao mudar aba
  useEffect(() => {
    carregarRelatorio(abaAtiva);
  }, [abaAtiva]);

  // Aplicar filtros manualmente (não automático)
  const aplicarFiltros = () => {
    carregarRelatorio(abaAtiva);
  };

  // ========================================
  // FORMATAÇÃO
  // ========================================

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(valor);
  };

  const formatarPercentual = (valor) => {
    return `${valor.toFixed(2)}%`;
  };

  // ========================================
  // EXPORTAÇÃO
  // ========================================

  const exportarCSV = async () => {
    try {
      const params = {
        tipo: abaAtiva,
        data_inicio: dataInicio,
        data_fim: dataFim,
      };

      const response = await api.get("/relatorios-comissoes/exportar-csv", {
        params,
        responseType: "blob",
      });

      // Download do arquivo
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `relatorio_${abaAtiva}_${new Date().toISOString().split("T")[0]}.csv`,
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error("Erro ao exportar CSV:", error);
      alert("Erro ao exportar arquivo");
    }
  };

  // ========================================
  // CORES E TEMAS
  // ========================================

  const CORES = ["#8884d8", "#82ca9d", "#ffc658", "#ff7c7c", "#a28bd4", "#f48fb1"];

  const obterCorAlerta = (nivel) => {
    if (nivel === 3) return "text-red-700 bg-red-100 border-red-300";
    if (nivel === 2) return "text-orange-700 bg-orange-100 border-orange-300";
    return "text-yellow-700 bg-yellow-100 border-yellow-300";
  };

  // ========================================
  // RENDERIZAÇÃO: ABAS
  // ========================================

  const renderizarAbas = () => {
    const abas = [
      { id: "margem-produto", label: "📊 Margem por Produto", icone: "💰" },
      { id: "produtos-prejudiciais", label: "⚠️ Produtos Prejudiciais", icone: "🚨" },
      { id: "ranking-funcionarios", label: "👥 Ranking Funcionários", icone: "🏆" },
      { id: "ranking-produtos", label: "📦 Ranking Produtos", icone: "📈" },
      { id: "ranking-categorias", label: "📂 Ranking Categorias", icone: "🎯" },
      { id: "dre", label: "📑 Visão DRE", icone: "💼" },
    ];

    return (
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {abas.map((aba) => (
          <button
            key={aba.id}
            onClick={() => setAbaAtiva(aba.id)}
            className={`px-4 py-3 rounded-lg font-medium whitespace-nowrap transition-all ${
              abaAtiva === aba.id
                ? "bg-blue-600 text-white shadow-lg"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            <span className="text-xl mr-2">{aba.icone}</span>
            {aba.label}
          </button>
        ))}
      </div>
    );
  };

  // ========================================
  // RENDERIZAÇÃO: FILTROS
  // ========================================

  const renderizarFiltros = () => {
    return (
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">📅 Data Início</label>
            <input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">📅 Data Fim</label>
            <input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={aplicarFiltros}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition mt-6"
            >
              🔍 Buscar
            </button>

            <button
              onClick={() => {
                setDataInicio("");
                setDataFim("");
                carregarRelatorio(abaAtiva);
              }}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition mt-6"
            >
              🔄 Limpar
            </button>

            {[
              "margem-produto",
              "produtos-prejudiciais",
              "ranking-funcionarios",
              "ranking-produtos",
            ].includes(abaAtiva) && (
              <button
                onClick={exportarCSV}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition mt-6"
              >
                📥 Exportar CSV
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ========================================
  // RENDERIZAÇÃO: MARGEM POR PRODUTO
  // ========================================

  // ========================================

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate("/comissoes-listagem")}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-4"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Voltar para Demonstrativo
        </button>

        <h1 className="text-3xl font-bold text-gray-800">📊 Relatórios Analíticos de Comissões</h1>
        <p className="text-gray-600 mt-2">
          Análise de rentabilidade, margem e tomada de decisão estratégica
        </p>
      </div>

      {/* Abas de Navegação */}
      {renderizarAbas()}

      {/* Filtros */}
      {renderizarFiltros()}

      {/* Conteúdo da Aba Ativa */}
      {carregando ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600"></div>
        </div>
      ) : (
        <RelatoriosComissoesSections
          CORES={CORES}
          abaAtiva={abaAtiva}
          dadosDRE={dadosDRE}
          dadosMargemProduto={dadosMargemProduto}
          dadosProdutosPrejudiciais={dadosProdutosPrejudiciais}
          dadosRankingCategorias={dadosRankingCategorias}
          dadosRankingFuncionarios={dadosRankingFuncionarios}
          dadosRankingProdutos={dadosRankingProdutos}
          formatarMoeda={formatarMoeda}
          formatarPercentual={formatarPercentual}
          obterCorAlerta={obterCorAlerta}
        />
      )}
    </div>
  );
};

export default RelatoriosComissoes;
