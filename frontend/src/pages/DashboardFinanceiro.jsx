import {
  AlertCircle,
  BarChart2,
  DollarSign,
  FileText,
  ShoppingBag,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useEffect, useState } from "react";
import { FiHelpCircle } from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../api";
import AlertasIA from "../components/AlertasIA";
import { useTour } from "../hooks/useTour";
import { tourDashboard } from "../tours/tourDefinitions";

const DashboardFinanceiro = () => {
  const navigate = useNavigate();
  const { iniciarTour } = useTour("dashboard", tourDashboard);
  const [loading, setLoading] = useState(true);
  const [periodoDias, setPeriodoDias] = useState(30);
  const [resumo, setResumo] = useState({
    saldo_atual: 0,
    contas_receber: { total: 0, vencidas: 0 },
    contas_pagar: { total: 0, vencidas: 0 },
    vendas_periodo: {
      quantidade: 0,
      valor_total: 0,
      finalizadas: 0,
      ticket_medio: 0,
    },
    fluxo_periodo: { entradas: 0, saidas: 0, lucro: 0 },
  });
  const [entradasSaidas, setEntradasSaidas] = useState([]);
  const [contasVencidas, setContasVencidas] = useState({
    contas_receber: [],
    contas_pagar: [],
  });

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(valor || 0);
  };

  const formatarData = (dataStr) => {
    const data = new Date(dataStr);
    return data.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
    });
  };

  const carregarDados = async () => {
    setLoading(true);

    // Carregar resumo
    try {
      const resumoRes = await api.get(
        `/dashboard/resumo?periodo_dias=${periodoDias}`,
      );
      setResumo(resumoRes.data);
    } catch (err) {
      console.error("Erro ao carregar resumo:", err);
    }

    // Carregar entradas/saídas
    try {
      const entradasSaidasRes = await api.get(
        `/dashboard/entradas-saidas?periodo_dias=${periodoDias}`,
      );
      setEntradasSaidas(entradasSaidasRes.data);
    } catch (err) {
      console.error("Erro ao carregar entradas/saídas:", err);
    }

    // Carregar contas vencidas
    try {
      const contasVencidasRes = await api.get(
        `/dashboard/contas-vencidas?limite=5`,
      );
      setContasVencidas(contasVencidasRes.data);
    } catch (err) {
      console.error("Erro ao carregar contas vencidas:", err);
    }

    setLoading(false);
  };

  useEffect(() => {
    carregarDados();
  }, [periodoDias]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-4 bg-gray-50 min-h-screen">
      {/* Cabeçalho */}
      <div className="mb-4 flex flex-wrap justify-between items-center gap-2">
        <div className="flex items-center gap-2">
          <div>
            <h1 className="text-xl font-bold text-gray-800">Dashboard Financeiro</h1>
            <p className="text-xs text-gray-500">Visão consolidada do seu negócio</p>
          </div>
          <button
            onClick={iniciarTour}
            title="Ver tour guiado desta página"
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          >
            <FiHelpCircle className="text-sm" />
          </button>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className="flex gap-1">
            {[{ v: 1, label: "Hoje" }, { v: 7, label: "7d" }, { v: 15, label: "15d" }, { v: 30, label: "30d" }, { v: 60, label: "60d" }, { v: 90, label: "90d" }].map(({ v, label }) => (
              <button
                key={v}
                onClick={() => setPeriodoDias(v)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  periodoDias === v
                    ? "bg-blue-600 text-white"
                    : "bg-white text-gray-600 hover:bg-gray-100 border border-gray-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-400">Período afeta: Lucro · Vendas · Fluxo · Ticket Médio</p>
        </div>
      </div>

      {/* KPIs — linha 1: valores fixos (não afetados pelo período) */}
      <div className="mb-1">
        <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-1.5">📌 Posição atual — não muda com o período</p>
        <div id="tour-stats" className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Saldo */}
        <div
          onClick={() => navigate("/financeiro/fluxo-caixa")}
          className="bg-blue-600 rounded-xl p-3 text-white cursor-pointer hover:bg-blue-700 transition-colors"
        >
          <div className="flex justify-between items-start mb-2">
            <DollarSign className="w-4 h-4 opacity-80" />
            <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">Hoje</span>
          </div>
          <p className="text-xs opacity-75 mb-0.5">Saldo Estimado</p>
          <p className="text-base font-bold leading-tight">{formatarMoeda(resumo.saldo_atual)}</p>
        </div>

        {/* A Receber */}
        <div
          onClick={() => navigate("/financeiro/contas-receber")}
          className="bg-emerald-600 rounded-xl p-3 text-white cursor-pointer hover:bg-emerald-700 transition-colors"
        >
          <div className="flex justify-between items-start mb-2">
            <TrendingUp className="w-4 h-4 opacity-80" />
            {resumo.contas_receber.vencidas > 0 && (
              <AlertCircle className="w-3.5 h-3.5 text-yellow-300" />
            )}
          </div>
          <p className="text-xs opacity-75 mb-0.5">A Receber</p>
          <p className="text-base font-bold leading-tight">{formatarMoeda(resumo.contas_receber.total)}</p>
          {resumo.contas_receber.vencidas > 0 && (
            <p className="text-xs mt-1 text-yellow-200">⚠ {formatarMoeda(resumo.contas_receber.vencidas)} venc.</p>
          )}
        </div>

        {/* A Pagar */}
        <div
          onClick={() => navigate("/financeiro/contas-pagar")}
          className="bg-red-500 rounded-xl p-3 text-white cursor-pointer hover:bg-red-600 transition-colors"
        >
          <div className="flex justify-between items-start mb-2">
            <TrendingDown className="w-4 h-4 opacity-80" />
            {resumo.contas_pagar.vencidas > 0 && (
              <AlertCircle className="w-3.5 h-3.5 text-yellow-300" />
            )}
          </div>
          <p className="text-xs opacity-75 mb-0.5">A Pagar</p>
          <p className="text-base font-bold leading-tight">{formatarMoeda(resumo.contas_pagar.total)}</p>
          {resumo.contas_pagar.vencidas > 0 && (
            <p className="text-xs mt-1 text-yellow-200">⚠ {formatarMoeda(resumo.contas_pagar.vencidas)} venc.</p>
          )}
        </div>
        </div>
      </div>

      {/* KPIs — linha 2: valores do período selecionado */}
      <div className="mb-4">
        <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-1.5 mt-3">📅 Período selecionado: {periodoDias === 1 ? "Hoje" : `últimos ${periodoDias} dias`}</p>
        <div className="grid grid-cols-3 gap-3">
          {/* Lucro do período */}
          <div
            onClick={() => navigate("/financeiro/dre")}
            className={`rounded-xl p-3 text-white cursor-pointer transition-colors ${
              resumo.fluxo_periodo.lucro >= 0
                ? "bg-purple-600 hover:bg-purple-700"
                : "bg-orange-500 hover:bg-orange-600"
            }`}
          >
            <div className="flex justify-between items-start mb-2">
              <FileText className="w-4 h-4 opacity-80" />
              <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">{periodoDias === 1 ? "Hoje" : `${periodoDias}d`}</span>
            </div>
            <p className="text-xs opacity-75 mb-0.5">
              {resumo.fluxo_periodo.lucro >= 0 ? "Lucro" : "Prejuízo"}
            </p>
            <p className="text-base font-bold leading-tight">
              {formatarMoeda(Math.abs(resumo.fluxo_periodo.lucro))}
            </p>
          </div>

          {/* Vendas (qtd) */}
          <div
            onClick={() => navigate("/financeiro/relatorio-vendas")}
            className="bg-cyan-600 rounded-xl p-3 text-white cursor-pointer hover:bg-cyan-700 transition-colors"
          >
            <div className="flex justify-between items-start mb-2">
              <ShoppingBag className="w-4 h-4 opacity-80" />
              <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">{periodoDias === 1 ? "Hoje" : `${periodoDias}d`}</span>
            </div>
            <p className="text-xs opacity-75 mb-0.5">Vendas</p>
            <p className="text-base font-bold leading-tight">
              {resumo.vendas_periodo.quantidade || 0}
            </p>
            <p className="text-xs opacity-75 mt-0.5">
              {formatarMoeda(resumo.vendas_periodo.valor_total)}
            </p>
          </div>

          {/* Ticket Médio */}
          <div
            onClick={() => navigate("/financeiro/relatorio-vendas")}
            className="bg-indigo-500 rounded-xl p-3 text-white cursor-pointer hover:bg-indigo-600 transition-colors"
          >
            <div className="flex justify-between items-start mb-2">
              <BarChart2 className="w-4 h-4 opacity-80" />
              <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">{periodoDias === 1 ? "Hoje" : `${periodoDias}d`}</span>
            </div>
            <p className="text-xs opacity-75 mb-0.5">Ticket Médio</p>
            <p className="text-base font-bold leading-tight">
              {formatarMoeda(resumo.vendas_periodo.ticket_medio || 0)}
            </p>
            <p className="text-xs opacity-75 mt-0.5">por venda</p>
          </div>
        </div>

        {/* Sub-row: Entradas, Saídas, Margem, Finalizadas */}
        <div id="tour-financeiro" className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2">
          <div className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">Entradas</p>
            <p className="text-lg font-bold text-emerald-600">{formatarMoeda(resumo.fluxo_periodo.entradas)}</p>
          </div>
          <div className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">Saídas</p>
            <p className="text-lg font-bold text-red-500">{formatarMoeda(resumo.fluxo_periodo.saidas)}</p>
          </div>
          <div className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">Margem</p>
            <p className="text-lg font-bold text-gray-800">
              {resumo.fluxo_periodo.entradas > 0
                ? ((resumo.fluxo_periodo.lucro / resumo.fluxo_periodo.entradas) * 100).toFixed(1) + "%"
                : "—"}
            </p>
          </div>
          <div className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">Finalizadas</p>
            <p className="text-lg font-bold text-gray-800">{resumo.vendas_periodo.finalizadas || 0}</p>
            <p className="text-xs text-gray-400">de {resumo.vendas_periodo.quantidade || 0} vendas</p>
          </div>
        </div>
      </div>

      {/* Gráfico + Alertas IA lado a lado */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-4">
        {/* Gráfico de fluxo */}
        <div id="tour-composicao" className="lg:col-span-3 bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            📈 Fluxo Financeiro — últimos {periodoDias} dias
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={entradasSaidas} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="gradEntradas" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradSaidas" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF4444" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="data"
                tickFormatter={formatarData}
                style={{ fontSize: "10px" }}
                tick={{ fill: "#9ca3af" }}
              />
              <YAxis
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                style={{ fontSize: "10px" }}
                tick={{ fill: "#9ca3af" }}
                width={36}
              />
              <Tooltip
                formatter={(value) => formatarMoeda(value)}
                labelFormatter={formatarData}
                contentStyle={{ fontSize: "12px" }}
              />
              <Legend wrapperStyle={{ fontSize: "11px" }} />
              <Area
                type="monotone"
                dataKey="entradas"
                stroke="#10B981"
                strokeWidth={2}
                fill="url(#gradEntradas)"
                name="Entradas"
              />
              <Area
                type="monotone"
                dataKey="saidas"
                stroke="#EF4444"
                strokeWidth={2}
                fill="url(#gradSaidas)"
                name="Saídas"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Alertas IA */}
        <div id="tour-acoes-rapidas" className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <AlertasIA compacto />
        </div>
      </div>

      {/* Contas Vencidas */}
      {(contasVencidas.contas_receber.length > 0 || contasVencidas.contas_pagar.length > 0) && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-red-100">
          <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500" />
            Contas Vencidas com Atenção
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {contasVencidas.contas_receber.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-2">
                  A Receber ({contasVencidas.contas_receber.length})
                </p>
                <div className="space-y-1.5">
                  {contasVencidas.contas_receber.slice(0, 3).map((conta) => (
                    <div key={conta.id} className="flex justify-between items-center p-2 bg-red-50 border border-red-100 rounded-lg">
                      <div>
                        <p className="text-xs font-medium text-gray-700">{conta.cliente || "Sem cliente"}</p>
                        <p className="text-xs text-red-500">Venceu há {conta.dias_vencido} dias</p>
                      </div>
                      <p className="text-sm font-bold text-red-600">{formatarMoeda(conta.saldo)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {contasVencidas.contas_pagar.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-2">
                  A Pagar ({contasVencidas.contas_pagar.length})
                </p>
                <div className="space-y-1.5">
                  {contasVencidas.contas_pagar.slice(0, 3).map((conta) => (
                    <div key={conta.id} className="flex justify-between items-center p-2 bg-orange-50 border border-orange-100 rounded-lg">
                      <div>
                        <p className="text-xs font-medium text-gray-700">{conta.fornecedor || "Sem fornecedor"}</p>
                        <p className="text-xs text-orange-500">Venceu há {conta.dias_vencido} dias</p>
                      </div>
                      <p className="text-sm font-bold text-orange-600">{formatarMoeda(conta.saldo)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardFinanceiro;
