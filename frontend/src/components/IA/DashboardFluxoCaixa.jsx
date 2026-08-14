/**
 * ABA 5: Dashboard Fluxo de Caixa Preditivo
 *
 * Dashboard principal com:
 * - Cards de índices de saúde
 * - Gráfico de projeções 15 dias
 * - Alertas automáticos
 * - Simulador de cenários
 */

import { useState, useEffect } from "react";
import api from "../../api";
import { getAccessToken } from "../../auth/tokenStorage";
import { toast } from "react-hot-toast";
import { RefreshCw } from "lucide-react";

import IndicesSaudeCards from "./IndicesSaudeCards";
import GraficoProjecoes from "./GraficoProjecoes";
import AlertasCaixa from "./AlertasCaixa";
import SimuladorCenarios from "./SimuladorCenarios";
import InfoMetricas from "./InfoMetricas";

export default function DashboardFluxoCaixa({ userId }) {
  const [loading, setLoading] = useState(true);
  const [indices, setIndices] = useState(null);
  const [projecoes, setProjecoes] = useState([]);
  const [alertas, setAlertas] = useState([]);
  const [abaAtiva, setAbaAtiva] = useState("visao-geral"); // visao-geral, projecoes, alertas, simulador

  // Carregar dados ao montar
  useEffect(() => {
    carregarDados();
  }, [userId]);

  const carregarDados = async () => {
    setLoading(true);
    try {
      const token = getAccessToken();
      const headers = { Authorization: `Bearer ${token}` };

      // Carregar índices, projeções e alertas em paralelo
      const [indicesRes, projecoesRes, alertasRes] = await Promise.all([
        api.get(`/ia/fluxo/indices-saude/${userId}`, { headers }),
        api.get(`/ia/fluxo/projecoes/${userId}?dias=15`, { headers }),
        api.get(`/ia/fluxo/alertas/${userId}`, { headers }),
      ]);

      setIndices(indicesRes.data);
      setProjecoes(projecoesRes.data || []);
      setAlertas(alertasRes.data || []);
    } catch (error) {
      console.error("Erro ao carregar dados IA:", error);
      toast.error("Erro ao carregar dados da IA");
    } finally {
      setLoading(false);
    }
  };

  const gerarNovaProjecao = async () => {
    const toastId = toast.loading("Gerando projeção com Prophet...");
    try {
      const token = getAccessToken();
      const headers = { Authorization: `Bearer ${token}` };

      await api.post(`/ia/fluxo/projetar-15-dias/${userId}`, {}, { headers });

      toast.success("Projeção gerada com sucesso!", { id: toastId });
      carregarDados();
    } catch (error) {
      console.error("Erro ao gerar projeção:", error);
      toast.error("Erro ao gerar projeção", { id: toastId });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Painel Informativo */}
      <InfoMetricas />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🤖 Fluxo de Caixa Preditivo</h1>
          <p className="text-gray-600 mt-1">Inteligência artificial analisando seu caixa</p>
        </div>

        <button
          onClick={gerarNovaProjecao}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Atualizar Projeção
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        <button
          onClick={() => setAbaAtiva("visao-geral")}
          className={`px-4 py-2 font-medium transition-colors ${
            abaAtiva === "visao-geral"
              ? "border-b-2 border-blue-600 text-blue-600"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          Visão Geral
        </button>
        <button
          onClick={() => setAbaAtiva("projecoes")}
          className={`px-4 py-2 font-medium transition-colors ${
            abaAtiva === "projecoes"
              ? "border-b-2 border-blue-600 text-blue-600"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          Projeções 15 Dias
        </button>
        <button
          onClick={() => setAbaAtiva("alertas")}
          className={`px-4 py-2 font-medium transition-colors relative ${
            abaAtiva === "alertas"
              ? "border-b-2 border-blue-600 text-blue-600"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          Alertas
          {alertas.length > 0 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {alertas.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setAbaAtiva("simulador")}
          className={`px-4 py-2 font-medium transition-colors ${
            abaAtiva === "simulador"
              ? "border-b-2 border-blue-600 text-blue-600"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          Simulador
        </button>
      </div>

      {/* Conteúdo */}
      <div className="space-y-6">
        {abaAtiva === "visao-geral" && (
          <>
            <div className="bg-gradient-to-r from-green-50 to-blue-50 border-l-4 border-green-500 p-4 rounded">
              <p className="text-sm text-gray-700">
                <strong>📊 Visão Geral:</strong> Análise dos últimos <strong>30 dias</strong> para
                calcular a saúde do caixa. Mostra quanto tempo você consegue manter o negócio com
                saldo atual.
              </p>
            </div>
            <IndicesSaudeCards indices={indices} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <GraficoProjecoes projecoes={projecoes.slice(0, 7)} titulo="Próximos 7 Dias" />
              <AlertasCaixa alertas={alertas.slice(0, 3)} />
            </div>
          </>
        )}

        {abaAtiva === "projecoes" && (
          <>
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-500 p-4 rounded">
              <p className="text-sm text-gray-700">
                <strong>📈 Projeção 15 Dias:</strong> Previsão usando inteligência artificial
                (Prophet). Baseada em <strong>30+ dias de histórico</strong> para prever entradas e
                saídas dos próximos <strong>15 dias</strong>. Quanto mais histórico, mais precisa a
                previsão.
              </p>
            </div>
            <GraficoProjecoes
              projecoes={projecoes}
              titulo="Projeção 15 Dias com Prophet"
              detalhado
            />
          </>
        )}

        {abaAtiva === "alertas" && (
          <>
            <div className="bg-gradient-to-r from-orange-50 to-red-50 border-l-4 border-orange-500 p-4 rounded">
              <p className="text-sm text-gray-700">
                <strong>Alertas:</strong> Avisos automáticos gerados em tempo real.
                <strong> Crítico</strong> = menos de 7 dias de caixa (risco iminente).
                <strong> Alerta</strong> = 7-15 dias (atenção necessária).
                <strong> OK</strong> = mais de 15 dias (situação confortável).
              </p>
            </div>
            <AlertasCaixa alertas={alertas} />
          </>
        )}

        {abaAtiva === "simulador" && (
          <>
            <div className="bg-gradient-to-r from-purple-50 to-pink-50 border-l-4 border-purple-500 p-4 rounded">
              <p className="text-sm text-gray-700">
                <strong>🎯 Simulador:</strong> Teste 3 cenários para os{" "}
                <strong>próximos 15 dias</strong>.<strong> Otimista:</strong> +20% receita, -10%
                despesa.
                <strong> Realista:</strong> sem mudanças.
                <strong> Pessimista:</strong> -20% receita, +10% despesa.
                <strong>Seus dados reais não são alterados!</strong>
              </p>
            </div>
            <SimuladorCenarios userId={userId} projecoesBase={projecoes} />
          </>
        )}
      </div>
    </div>
  );
}
