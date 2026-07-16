import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Building2,
  CheckCircle2,
  HelpCircle,
  Clock3,
  MessageCircle,
  RefreshCw,
  ShoppingBag,
  TrendingDown,
  TrendingUp,
  Users,
  WalletCards,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { useTour } from "../hooks/useTour";
import { tourDashboard } from "../tours/tourDefinitions";
import { formatMoneyBRL } from "../utils/formatters";
import { DashboardLoading, MetricCard, PriorityCard } from "./dashboard/DashboardCards";
import {
  calculateDashboardIndicators,
  createEmptyDashboardSummary,
  createEmptyManagementMetrics,
  getExecutiveStatus,
  getPeriodLabel,
} from "./dashboard/dashboardOverview";

const PERIOD_OPTIONS = [
  { value: 1, label: "Hoje" },
  { value: 7, label: "7 dias" },
  { value: 15, label: "15 dias" },
  { value: 30, label: "30 dias" },
  { value: 60, label: "60 dias" },
  { value: 90, label: "90 dias" },
];

const STATUS_STYLES = {
  neutral:
    "border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200",
  positive:
    "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200",
  warning:
    "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200",
  critical:
    "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200",
};

function formatDate(dateValue) {
  if (!dateValue) return "-";
  return new Date(dateValue).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export default function DashboardFinanceiro() {
  const navigate = useNavigate();
  const { iniciarTour } = useTour("dashboard", tourDashboard, { delay: 2000 });
  const requestIdRef = useRef(0);
  const hasLoadedRef = useRef(false);
  const [periodDays, setPeriodDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [failedBlocks, setFailedBlocks] = useState([]);
  const [summary, setSummary] = useState(createEmptyDashboardSummary);
  const [management, setManagement] = useState(createEmptyManagementMetrics);
  const [cashFlow, setCashFlow] = useState([]);
  const [overdueAccounts, setOverdueAccounts] = useState({ contas_receber: [], contas_pagar: [] });
  const [topProducts, setTopProducts] = useState([]);
  const [bankBalance, setBankBalance] = useState(null);

  const loadDashboard = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    if (hasLoadedRef.current) setRefreshing(true);
    else setLoading(true);

    const requests = [
      {
        key: "resumo financeiro",
        promise: api.get("/dashboard/resumo", { params: { periodo_dias: periodDays } }),
      },
      {
        key: "fluxo diário",
        promise: api.get("/dashboard/entradas-saidas", { params: { periodo_dias: periodDays } }),
      },
      {
        key: "contas vencidas",
        promise: api.get("/dashboard/contas-vencidas", { params: { limite: 5 } }),
      },
      { key: "clientes", promise: api.get("/dashboard/gerencial") },
      {
        key: "produtos",
        promise: api.get("/dashboard/top-produtos", {
          params: { periodo_dias: periodDays, limite: 5 },
        }),
      },
      { key: "saldo bancário", promise: api.get("/contas-bancarias/resumo/saldos") },
    ];

    const results = await Promise.allSettled(requests.map((request) => request.promise));
    if (requestId !== requestIdRef.current) return;

    const failed = [];
    results.forEach((result, index) => {
      if (result.status === "rejected") failed.push(requests[index].key);
    });

    if (results[0].status === "fulfilled") setSummary(results[0].value.data);
    if (results[1].status === "fulfilled") setCashFlow(results[1].value.data || []);
    if (results[2].status === "fulfilled") setOverdueAccounts(results[2].value.data);
    if (results[3].status === "fulfilled") setManagement(results[3].value.data);
    if (results[4].status === "fulfilled") setTopProducts(results[4].value.data || []);
    if (results[5].status === "fulfilled") {
      setBankBalance(Number(results[5].value.data?.total_geral || 0));
    } else {
      setBankBalance(null);
    }

    hasLoadedRef.current = true;
    setFailedBlocks(failed);
    setLastUpdate(new Date());
    setLoading(false);
    setRefreshing(false);
  }, [periodDays]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const indicators = useMemo(() => calculateDashboardIndicators(summary), [summary]);
  const executiveStatus = useMemo(() => getExecutiveStatus(summary), [summary]);
  const statusIcon = executiveStatus.tone === "positive" ? CheckCircle2 : AlertCircle;
  const StatusIcon = statusIcon;
  const periodLabel = getPeriodLabel(periodDays);
  const salesTotal = Number(summary?.vendas_periodo?.valor_total || 0);
  const grossSales = Number(summary?.vendas_periodo?.faturamento_bruto || 0);
  const cashResult = Number(summary?.fluxo_periodo?.lucro || 0);
  const displayedBalance = bankBalance ?? Number(summary?.saldo_atual || 0);
  const hasChartMovement = cashFlow.some(
    (item) => Number(item?.entradas || 0) !== 0 || Number(item?.saidas || 0) !== 0,
  );

  const openManagementAssistant = () => {
    navigate("/ia/chat", {
      state: {
        perguntaInicial: `Analise meu negócio nos últimos ${periodDays} dias: vendas, resultado de caixa, contas vencidas e riscos de clientes.`,
      },
    });
  };

  if (loading) return <DashboardLoading />;

  return (
    <div className="min-h-full space-y-5 bg-slate-50 p-4 dark:bg-slate-950 sm:p-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${STATUS_STYLES[executiveStatus.tone]}`}
              >
                <StatusIcon className="h-3.5 w-3.5" />
                {executiveStatus.title}
              </span>
              {lastUpdate && (
                <span className="text-xs text-slate-400">
                  Atualizado às{" "}
                  {lastUpdate.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-slate-950 dark:text-white sm:text-3xl">
              Visão geral do negócio
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-400">
              {executiveStatus.description} Os valores abaixo separam a posição atual do desempenho
              do período.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={iniciarTour}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              title="Conhecer o dashboard"
            >
              <HelpCircle className="h-4 w-4" />
              <span className="hidden sm:inline">Entender painel</span>
            </button>
            <button
              type="button"
              onClick={openManagementAssistant}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 dark:bg-cyan-500 dark:text-slate-950 dark:hover:bg-cyan-400"
            >
              <MessageCircle className="h-4 w-4" />
              Analisar com IA
            </button>
            <button
              type="button"
              onClick={loadDashboard}
              disabled={refreshing}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              Atualizar
            </button>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
          <span className="mr-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Período
          </span>
          {PERIOD_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setPeriodDays(option.value)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                periodDays === option.value
                  ? "bg-[#0f8b8d] text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>

      {failedBlocks.length > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>
            Parte do painel não pôde ser atualizada ({failedBlocks.join(", ")}). Os demais números
            continuam disponíveis.
          </p>
        </div>
      )}

      <section id="tour-stats">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Desempenho</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">{periodLabel}</p>
          </div>
          <div className="flex gap-4 text-xs text-slate-500 dark:text-slate-400">
            <span>
              Entradas:{" "}
              <strong className="text-emerald-700 dark:text-emerald-300">
                {formatMoneyBRL(indicators.inflows)}
              </strong>
            </span>
            <span>
              Saídas:{" "}
              <strong className="text-rose-700 dark:text-rose-300">
                {formatMoneyBRL(indicators.outflows)}
              </strong>
            </span>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            icon={TrendingUp}
            label="Faturamento"
            value={formatMoneyBRL(salesTotal)}
            detail={
              grossSales > salesTotal
                ? `Bruto antes de descontos: ${formatMoneyBRL(grossSales)}`
                : "Total das vendas finalizadas"
            }
            tone="violet"
            onClick={() => navigate("/financeiro/vendas")}
          />
          <MetricCard
            icon={cashResult >= 0 ? TrendingUp : TrendingDown}
            label="Resultado de caixa"
            value={formatMoneyBRL(cashResult)}
            detail={`${formatMoneyBRL(indicators.inflows)} em entradas − ${formatMoneyBRL(indicators.outflows)} em saídas`}
            tone={cashResult >= 0 ? "emerald" : "rose"}
            onClick={() => navigate("/financeiro/fluxo-caixa")}
          />
          <MetricCard
            icon={ShoppingBag}
            label="Vendas finalizadas"
            value={String(summary?.vendas_periodo?.quantidade || 0)}
            detail="Quantidade concluída no período"
            tone="cyan"
            onClick={() => navigate("/financeiro/vendas")}
          />
          <MetricCard
            icon={BarChart3}
            label="Ticket médio"
            value={formatMoneyBRL(summary?.vendas_periodo?.ticket_medio || 0)}
            detail="Valor médio por venda finalizada"
            tone="blue"
            onClick={() => navigate("/financeiro/vendas")}
          />
        </div>
      </section>

      <section id="tour-financeiro" className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 xl:col-span-1">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Posição atual</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Valores acumulados, sem filtro de período
            </p>
          </div>
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => navigate("/financeiro/bancos")}
              className="flex w-full items-center justify-between rounded-xl bg-slate-900 p-4 text-left text-white transition hover:bg-slate-800 dark:bg-cyan-500 dark:text-slate-950 dark:hover:bg-cyan-400"
            >
              <span>
                <span className="block text-xs opacity-70">
                  {bankBalance === null ? "Saldo estimado" : "Saldo em bancos"}
                </span>
                <strong className="mt-1 block text-xl">{formatMoneyBRL(displayedBalance)}</strong>
              </span>
              <Building2 className="h-5 w-5 opacity-70" />
            </button>
            <button
              type="button"
              onClick={() => navigate("/financeiro/contas-receber")}
              className="flex w-full items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-left transition hover:bg-emerald-100 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:hover:bg-emerald-500/15"
            >
              <span>
                <span className="block text-xs text-emerald-700 dark:text-emerald-300">
                  Total a receber
                </span>
                <strong className="mt-1 block text-lg text-emerald-950 dark:text-emerald-100">
                  {formatMoneyBRL(summary?.contas_receber?.total || 0)}
                </strong>
              </span>
              <TrendingUp className="h-5 w-5 text-emerald-600" />
            </button>
            <button
              type="button"
              onClick={() => navigate("/financeiro/contas-pagar")}
              className="flex w-full items-center justify-between rounded-xl border border-rose-200 bg-rose-50 p-4 text-left transition hover:bg-rose-100 dark:border-rose-500/30 dark:bg-rose-500/10 dark:hover:bg-rose-500/15"
            >
              <span>
                <span className="block text-xs text-rose-700 dark:text-rose-300">
                  Total a pagar
                </span>
                <strong className="mt-1 block text-lg text-rose-950 dark:text-rose-100">
                  {formatMoneyBRL(summary?.contas_pagar?.total || 0)}
                </strong>
              </span>
              <TrendingDown className="h-5 w-5 text-rose-600" />
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 xl:col-span-2">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Atenção agora</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Pendências que podem virar ação, sem misturar com indicadores
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <PriorityCard
              icon={WalletCards}
              label="Recebimentos vencidos"
              value={formatMoneyBRL(indicators.overdueReceivable)}
              detail={
                indicators.overdueReceivable > 0
                  ? "Priorize as cobranças mais antigas"
                  : "Nenhum valor vencido"
              }
              hasIssue={indicators.overdueReceivable > 0}
              onClick={() => navigate("/financeiro/contas-receber")}
            />
            <PriorityCard
              icon={Clock3}
              label="Pagamentos vencidos"
              value={formatMoneyBRL(indicators.overduePayable)}
              detail={
                indicators.overduePayable > 0
                  ? "Revise juros e fornecedores prioritários"
                  : "Nenhum valor vencido"
              }
              hasIssue={indicators.overduePayable > 0}
              onClick={() => navigate("/financeiro/contas-pagar")}
            />
            <PriorityCard
              icon={Users}
              label="VIPs em risco"
              value={String(management?.vips_inativos?.quantidade || 0)}
              detail={
                management?.vips_inativos?.quantidade > 0
                  ? `${management.vips_inativos.impacto} em impacto estimado`
                  : "Nenhum VIP inativo há mais de 20 dias"
              }
              hasIssue={Number(management?.vips_inativos?.quantidade || 0) > 0}
              onClick={() => navigate("/clientes")}
            />
            <PriorityCard
              icon={Users}
              label="Clientes inativos"
              value={String(management?.clientes_inativos?.quantidade || 0)}
              detail={
                management?.clientes_inativos?.quantidade > 0
                  ? "Sem compra há mais de 90 dias"
                  : "Nenhum cliente nessa condição"
              }
              hasIssue={Number(management?.clientes_inativos?.quantidade || 0) > 0}
              onClick={() => navigate("/clientes")}
            />
          </div>
        </div>
      </section>

      <section id="tour-composicao" className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 xl:col-span-3">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Entradas e saídas
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Movimento diário · {periodLabel.toLowerCase()}
              </p>
            </div>
          </div>
          {hasChartMovement ? (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={cashFlow} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="dashboardEntradas" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0f8b8d" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0f8b8d" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="dashboardSaidas" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e11d48" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#e11d48" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="data"
                  tickFormatter={formatDate}
                  tick={{ fill: "#64748b", fontSize: 11 }}
                />
                <YAxis
                  width={54}
                  tickFormatter={(value) =>
                    Number(value).toLocaleString("pt-BR", { notation: "compact" })
                  }
                  tick={{ fill: "#64748b", fontSize: 11 }}
                />
                <Tooltip formatter={(value) => formatMoneyBRL(value)} labelFormatter={formatDate} />
                <Legend wrapperStyle={{ fontSize: "12px" }} />
                <Area
                  type="monotone"
                  dataKey="entradas"
                  stroke="#0f8b8d"
                  strokeWidth={2}
                  fill="url(#dashboardEntradas)"
                  name="Entradas"
                />
                <Area
                  type="monotone"
                  dataKey="saidas"
                  stroke="#e11d48"
                  strokeWidth={2}
                  fill="url(#dashboardSaidas)"
                  name="Saídas"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[260px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-center dark:border-slate-700 dark:bg-slate-950/40">
              <div>
                <BarChart3 className="mx-auto h-7 w-7 text-slate-300 dark:text-slate-600" />
                <p className="mt-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Sem movimento neste período
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Escolha outro período ou registre novas movimentações.
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 xl:col-span-2">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Produtos que puxam as vendas
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Ranking por quantidade no período
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/produtos")}
              className="text-xs font-semibold text-[#0f8b8d] hover:underline dark:text-cyan-300"
            >
              Ver produtos
            </button>
          </div>
          {topProducts.length > 0 ? (
            <ol className="space-y-2">
              {topProducts.map((product, index) => (
                <li
                  key={`${product.nome}-${index}`}
                  className="flex items-center gap-3 rounded-xl border border-slate-100 p-3 dark:border-slate-800"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#d8eee9] text-sm font-bold text-[#0f5f63] dark:bg-cyan-500/10 dark:text-cyan-300">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                      {product.nome}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {product.quantidade_vendida} unidades
                    </p>
                  </div>
                  <strong className="text-sm text-slate-700 dark:text-slate-200">
                    {formatMoneyBRL(product.receita_total)}
                  </strong>
                </li>
              ))}
            </ol>
          ) : (
            <div className="flex min-h-56 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-center dark:border-slate-700 dark:bg-slate-950/40">
              <div>
                <ShoppingBag className="mx-auto h-7 w-7 text-slate-300 dark:text-slate-600" />
                <p className="mt-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Sem produtos vendidos no período
                </p>
              </div>
            </div>
          )}
        </div>
      </section>

      <section id="tour-acoes-rapidas" className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Base de clientes</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Qualidade e oportunidade de relacionamento
          </p>
          <div className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
            {[
              ["Clientes ativos", management?.total_clientes || 0],
              ["Novos promissores", management?.oportunidades_novos?.quantidade || 0],
              ["Sem WhatsApp", management?.whatsapp_inativo?.quantidade || 0],
            ].map(([label, value]) => (
              <button
                key={label}
                type="button"
                onClick={() => navigate("/clientes")}
                className="flex w-full items-center justify-between py-3 text-left"
              >
                <span className="text-sm text-slate-600 dark:text-slate-400">{label}</span>
                <strong className="text-base text-slate-900 dark:text-white">{value}</strong>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 lg:col-span-2">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Contas vencidas mais antigas
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Detalhes para começar a agir sem procurar em outra tela
              </p>
            </div>
          </div>
          {overdueAccounts.contas_receber?.length || overdueAccounts.contas_pagar?.length ? (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {[
                {
                  key: "contas_receber",
                  label: "A receber",
                  personKey: "cliente",
                  path: "/financeiro/contas-receber",
                  tone: "text-emerald-700 dark:text-emerald-300",
                },
                {
                  key: "contas_pagar",
                  label: "A pagar",
                  personKey: "fornecedor",
                  path: "/financeiro/contas-pagar",
                  tone: "text-rose-700 dark:text-rose-300",
                },
              ].map((group) => (
                <div
                  key={group.key}
                  className="rounded-xl border border-slate-100 p-3 dark:border-slate-800"
                >
                  <button
                    type="button"
                    onClick={() => navigate(group.path)}
                    className={`mb-2 flex w-full items-center justify-between text-xs font-bold uppercase tracking-wide ${group.tone}`}
                  >
                    {group.label}
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                  <div className="space-y-2">
                    {(overdueAccounts[group.key] || []).slice(0, 3).map((account) => (
                      <div
                        key={account.id}
                        className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 p-2.5 dark:bg-slate-950/50"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
                            {account[group.personKey] || account.descricao || "Sem identificação"}
                          </p>
                          <p className="text-xs text-slate-400">
                            Vencida há {account.dias_vencido || 0} dias
                          </p>
                        </div>
                        <strong className="shrink-0 text-sm text-slate-700 dark:text-slate-200">
                          {formatMoneyBRL(account.saldo)}
                        </strong>
                      </div>
                    ))}
                    {(overdueAccounts[group.key] || []).length === 0 && (
                      <p className="py-6 text-center text-xs text-slate-400">
                        Nenhuma conta vencida
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex min-h-36 items-center justify-center rounded-xl border border-dashed border-emerald-200 bg-emerald-50/60 text-center dark:border-emerald-500/30 dark:bg-emerald-500/10">
              <div>
                <CheckCircle2 className="mx-auto h-7 w-7 text-emerald-600" />
                <p className="mt-2 text-sm font-semibold text-emerald-800 dark:text-emerald-200">
                  Nenhuma conta vencida
                </p>
                <p className="mt-1 text-xs text-emerald-700/70 dark:text-emerald-300/70">
                  Recebimentos e pagamentos estão em dia.
                </p>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
