/**
 * ETAPA 11.2 - Dashboard Financeiro de Entregas
 * ETAPA 11.3 - Gráficos
 * ETAPA 12.1 e 12.2 - IA (Análises e Sugestões)
 * 
 * Tela que exibe:
 * - KPIs consolidados de entregas concluídas
 * - Gráficos de custo e taxa
 * - Análises automáticas da IA
 * - Sugestões práticas da IA
 */
import { useEffect, useState } from "react";
import api from "../../api";
import { FiCalendar, FiRefreshCw, FiTruck, FiDollarSign, FiUser, FiTool, FiCreditCard, FiTrendingDown, FiAlertCircle, FiZap } from "react-icons/fi";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function DashEntregasFinanceiro() {
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [dados, setDados] = useState(null);
  const [graficos, setGraficos] = useState(null);
  const [ia, setIa] = useState(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState(null);

  async function carregarDados() {
    if (!dataInicio || !dataFim) {
      setErro("Selecione o período para consulta");
      return;
    }

    setLoading(true);
    setErro(null);
    
    try {
      // Carregar todos os dados em paralelo
      const [resDados, resGraficos, resIa] = await Promise.all([
        api.get("/dashboard/entregas/financeiro", {
          params: { data_inicio: dataInicio, data_fim: dataFim }
        }),
        api.get("/dashboard/entregas/financeiro/graficos", {
          params: { data_inicio: dataInicio, data_fim: dataFim }
        }),
        api.get("/dashboard/entregas/financeiro/ia", {
          params: { data_inicio: dataInicio, data_fim: dataFim }
        }).catch(() => null), // Se a IA falhar, continua normalmente
      ]);
      
      setDados(resDados.data);
      setGraficos(resGraficos.data);
      setIa(resIa?.data || { alertas: [], sugestoes: [] });
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      setErro(error.response?.data?.detail || "Erro ao carregar dados do dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Configurar período padrão: mês atual
    const hoje = new Date();
    const primeiroDia = new Date(hoje.getFullYear(), hoje.getMonth(), 1);

    setDataInicio(primeiroDia.toISOString().slice(0, 10));
    setDataFim(hoje.toISOString().slice(0, 10));
  }, []);

  useEffect(() => {
    if (dataInicio && dataFim) {
      carregarDados();
    }
  }, [dataInicio, dataFim]);

  // Análise de margem
  const analiseMargem = () => {
    if (!dados || dados.total_entregas === 0) return null;

    const margem = dados.margem_media;
    const cor = margem >= 0 ? "text-green-600" : "text-red-600";
    const icone = margem >= 0 ? "✅" : "⚠️";

    return (
      <div className={`p-4 border rounded-lg ${margem >= 0 ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">{icone}</span>
          <h3 className="font-semibold text-gray-700">Análise de Margem</h3>
        </div>
        <p className={`text-sm ${cor}`}>
          {margem >= 0 ? (
            <>
              A taxa de entrega está <strong>cobrindo os custos</strong> com uma margem média de <strong>{formatarMoeda(margem)}</strong> por entrega.
            </>
          ) : (
            <>
              ⚠️ A taxa de entrega está <strong>abaixo dos custos</strong>. Déficit médio de <strong>{formatarMoeda(Math.abs(margem))}</strong> por entrega.
            </>
          )}
        </p>
      </div>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Cabeçalho */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <FiTruck className="text-blue-600" />
          Dashboard Financeiro de Entregas
        </h1>
        <p className="text-gray-600 mt-1">
          Visualize os custos e receitas das entregas realizadas no período
        </p>
      </div>

      {/* Filtros */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <FiCalendar className="text-gray-500" />
            <label className="text-sm font-medium text-gray-700">Período:</label>
          </div>
          
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">De:</label>
            <input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Até:</label>
            <input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <button
            onClick={carregarDados}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <FiRefreshCw className={loading ? "animate-spin" : ""} />
            {loading ? "Carregando..." : "Atualizar"}
          </button>
        </div>
      </div>

      {/* Mensagem de Erro */}
      {erro && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 flex items-center gap-2">
          <FiAlertCircle />
          <span>{erro}</span>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="space-y-6">
          {/* Skeleton das Análises */}
          <div className="space-y-3">
            <AnalyseSkeleton />
            <AnalyseSkeleton />
          </div>

          {/* Skeleton dos KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => <KpiSkeleton key={i} />)}
          </div>

          {/* Skeleton dos Gráficos */}
          <ChartSkeleton />
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
      )}

      {/* Dados do Dashboard */}
      {!loading && dados && (
        <>
          {/* IA - Alertas */}
          {ia && ia.alertas && ia.alertas.length > 0 && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                <FiZap className="text-yellow-600" />
                Alertas Automáticos
              </h2>
              <div className="space-y-3">
                {ia.alertas.map((alerta, idx) => (
                  <div 
                    key={idx}
                    className="p-4 border border-yellow-200 bg-yellow-50 rounded-lg"
                  >
                    <p className="text-sm text-gray-700">{alerta}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* IA - Sugestões */}
          {ia && ia.sugestoes && ia.sugestoes.length > 0 && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                <span className="text-xl">💡</span>
                Sugestões Práticas
              </h2>
              <div className="space-y-3">
                {ia.sugestoes.map((sugestao, idx) => (
                  <div 
                    key={idx}
                    className="p-4 border border-blue-200 bg-blue-50 rounded-lg"
                  >
                    <p className="text-sm text-gray-700">{sugestao}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cards de KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <Card
              titulo="Total de Entregas"
              valor={dados.total_entregas}
              icon={<FiTruck className="text-blue-600" />}
              colorClasse="border-blue-200 bg-blue-50"
            />
            <Card
              titulo="Custo Total"
              valor={formatarMoeda(dados.custo_total_entregas)}
              icon={<FiDollarSign className="text-red-600" />}
              colorClasse="border-red-200 bg-red-50"
              subtitulo="Entregadores + Moto"
            />
            <Card
              titulo="Custo Entregadores"
              valor={formatarMoeda(dados.custo_total_entregadores)}
              icon={<FiUser className="text-purple-600" />}
              colorClasse="border-purple-200 bg-purple-50"
            />
            <Card
              titulo="Custo da Moto"
              valor={formatarMoeda(dados.custo_total_moto)}
              icon={<FiTool className="text-orange-600" />}
              colorClasse="border-orange-200 bg-orange-50"
            />
            <Card
              titulo="Repasse aos Entregadores"
              valor={formatarMoeda(dados.total_repasse_taxa)}
              icon={<FiCreditCard className="text-green-600" />}
              colorClasse="border-green-200 bg-green-50"
            />
            <Card
              titulo="Custo Médio por Entrega"
              valor={formatarMoeda(dados.custo_medio_por_entrega)}
              icon={<FiTrendingDown className="text-indigo-600" />}
              colorClasse="border-indigo-200 bg-indigo-50"
            />
          </div>

          {/* Análise de Margem */}
          {analiseMargem()}

          {/* Gráficos */}
          {graficos && (
            <div className="space-y-6 mt-6">
              {/* Gráfico 1: Custo total por dia */}
              {graficos.por_dia && graficos.por_dia.length > 0 && (
                <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    📈 Custo Total por Dia
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Responde: "Estou gastando mais?"
                  </p>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={graficos.por_dia}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="data" 
                        tick={{ fontSize: 12 }}
                        tickFormatter={(value) => {
                          const [ano, mes, dia] = value.split('-');
                          return `${dia}/${mes}`;
                        }}
                      />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip 
                        formatter={(value) => `R$ ${Number(value).toFixed(2)}`}
                        labelFormatter={(label) => {
                          const [ano, mes, dia] = label.split('-');
                          return `${dia}/${mes}/${ano}`;
                        }}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="custo" 
                        stroke="#ef4444" 
                        strokeWidth={2}
                        name="Custo Total (R$)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Gráfico 2: Custo médio por entrega */}
              {graficos.custo_medio && graficos.custo_medio.length > 0 && (
                <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    📉 Custo Médio por Entrega
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Responde: "Entregar está ficando caro?"
                  </p>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={graficos.custo_medio}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="data" 
                        tick={{ fontSize: 12 }}
                        tickFormatter={(value) => {
                          const [ano, mes, dia] = value.split('-');
                          return `${dia}/${mes}`;
                        }}
                      />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip 
                        formatter={(value) => `R$ ${Number(value).toFixed(2)}`}
                        labelFormatter={(label) => {
                          const [ano, mes, dia] = label.split('-');
                          return `${dia}/${mes}/${ano}`;
                        }}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="valor" 
                        stroke="#8b5cf6" 
                        strokeWidth={2}
                        name="Custo Médio (R$)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Gráfico 3: Taxa cobrada x Custo real */}
              {graficos.taxa_vs_custo && (
                <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    📊 Taxa Cobrada × Custo Real
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Responde: "A taxa cobre o custo?"
                  </p>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart 
                      data={[
                        { 
                          name: 'Média', 
                          'Taxa Cobrada': graficos.taxa_vs_custo.taxa_media,
                          'Custo Real': graficos.taxa_vs_custo.custo_medio
                        }
                      ]}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip formatter={(value) => `R$ ${Number(value).toFixed(2)}`} />
                      <Legend />
                      <Bar dataKey="Taxa Cobrada" fill="#10b981" />
                      <Bar dataKey="Custo Real" fill="#ef4444" />
                    </BarChart>
                  </ResponsiveContainer>
                  <div className="mt-4 text-center">
                    {graficos.taxa_vs_custo.taxa_media >= graficos.taxa_vs_custo.custo_medio ? (
                      <p className="text-green-600 font-medium">
                        ✅ Taxa média (R$ {graficos.taxa_vs_custo.taxa_media.toFixed(2)}) cobre o custo médio (R$ {graficos.taxa_vs_custo.custo_medio.toFixed(2)})
                      </p>
                    ) : (
                      <p className="text-red-600 font-medium">
                        ⚠️ Taxa média (R$ {graficos.taxa_vs_custo.taxa_media.toFixed(2)}) está abaixo do custo médio (R$ {graficos.taxa_vs_custo.custo_medio.toFixed(2)})
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Informações do Período */}
          <div className="mt-6 text-sm text-gray-500 text-center">
            Dados do período: {formatarData(dados.periodo.data_inicio)} até {formatarData(dados.periodo.data_fim)}
          </div>
        </>
      )}

      {/* Estado Vazio */}
      {!loading && dados && dados.total_entregas === 0 && (
        <div className="text-center py-12">
          <FiTruck className="mx-auto h-16 w-16 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-700 mb-2">
            Nenhuma entrega encontrada
          </h3>
          <p className="text-gray-500">
            Não há entregas concluídas no período selecionado
          </p>
        </div>
      )}
    </div>
  );
}

function Card({ titulo, valor, icon, colorClasse, subtitulo }) {
  return (
    <div className={`p-5 rounded-lg border shadow-sm ${colorClasse || "border-gray-200 bg-white"}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="text-2xl">{icon}</div>
      </div>
      <h4 className="text-sm font-medium text-gray-600 mb-1">{titulo}</h4>
      {subtitulo && (
        <p className="text-xs text-gray-500 mb-2">{subtitulo}</p>
      )}
      <div className="text-2xl font-bold text-gray-800">{valor}</div>
    </div>
  );
}

// Skeleton Components
function KpiSkeleton() {
  return (
    <div
      style={{
        height: 110,
        borderRadius: 8,
        background: 'linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s infinite',
      }}
    />
  );
}

function ChartSkeleton() {
  return (
    <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
      <div
        style={{
          height: 20,
          width: '40%',
          borderRadius: 4,
          background: 'linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s infinite',
          marginBottom: 16,
        }}
      />
      <div
        style={{
          height: 300,
          borderRadius: 8,
          background: 'linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s infinite',
        }}
      />
    </div>
  );
}

function AnalyseSkeleton() {
  return (
    <div
      style={{
        height: 80,
        borderRadius: 8,
        background: 'linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s infinite',
      }}
    />
  );
}

function formatarMoeda(valor) {
  if (valor === null || valor === undefined) return "R$ 0,00";
  return valor.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function formatarData(dataISO) {
  if (!dataISO) return "";
  const [ano, mes, dia] = dataISO.split("-");
  return `${dia}/${mes}/${ano}`;
}
