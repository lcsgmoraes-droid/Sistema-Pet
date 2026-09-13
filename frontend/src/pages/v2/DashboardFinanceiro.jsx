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
import api from "../../api";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoLink from "../../components/v2/BotaoLink/BotaoLink";
import CartaoIndicador from "../../components/v2/CartaoIndicador/CartaoIndicador";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import SeletorOpcoes from "../../components/v2/SeletorOpcoes/SeletorOpcoes";
import { TONS_BADGE } from "../../components/v2/utils/tons";
import { useTour } from "../../hooks/useTour";
import { useTheme } from "../../theme/ThemeContext";
import { tourDashboard } from "../../tours/tourDefinitions";
import { formatMoneyBRL } from "../../utils/formatters";
import { formatarDataLocal } from "../../components/financeiro/vendasFinanceiro/vendasFinanceiroDatas";
import {
  calculateDashboardIndicators,
  createEmptyDashboardSummary,
  createEmptyManagementMetrics,
  getDashboardDetailPath,
  getExecutiveStatus,
  getPeriodLabel,
} from "../dashboard/dashboardOverview";

const PERIOD_OPTIONS = [
  { valor: 1, rotulo: "Hoje" },
  { valor: 7, rotulo: "7 dias" },
  { valor: 15, rotulo: "15 dias" },
  { valor: 30, rotulo: "30 dias" },
  { valor: 60, rotulo: "60 dias" },
  { valor: 90, rotulo: "90 dias" },
];

function formatDate(dateValue) {
  if (!dateValue) return "-";
  return formatarDataLocal(dateValue, { day: "2-digit", month: "2-digit" });
}

function formatQuantity(value) {
  return Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 });
}

function DashboardLoading() {
  return (
    <div role="status" aria-live="polite" className="flex min-h-[65vh] items-center justify-center">
      <div className="text-center">
        <RefreshCw
          className="mx-auto h-8 w-8 motion-safe:animate-spin text-cyan-600 dark:text-cyan-400"
          aria-hidden="true"
        />
        <p className="mt-3 text-sm font-medium text-slate-600 dark:text-slate-300">
          Organizando os principais números...
        </p>
      </div>
    </div>
  );
}

export default function DashboardFinanceiro() {
  const navigate = useNavigate();
  const { isDark } = useTheme();
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
  const statusIcon = executiveStatus.tone === "sucesso" ? CheckCircle2 : AlertCircle;
  const StatusIcon = statusIcon;
  const periodLabel = getPeriodLabel(periodDays);
  const grossSales = Number(summary?.vendas_periodo?.faturamento_bruto || 0);
  const porRecebimento = summary?.visao_comercial === "recebimento";
  const commercialValue = summary?.indicador_comercial ?? grossSales;
  const cashResult = Number(summary?.fluxo_periodo?.lucro || 0);
  const salesCount = Number(summary?.vendas_periodo?.quantidade || 0);
  const unitsSold = Number(summary?.vendas_periodo?.unidades || 0);
  const salesProfit = Number(summary?.vendas_periodo?.lucro || 0);
  const displayedBalance = bankBalance ?? Number(summary?.saldo_atual || 0);
  const hasChartMovement = cashFlow.some(
    (item) => Number(item?.entradas || 0) !== 0 || Number(item?.saidas || 0) !== 0,
  );
  const chartGridColor = isDark ? "#334155" : "#e2e8f0";
  const chartTickColor = isDark ? "#94a3b8" : "#64748b";

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
      <section className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="mr-1 text-xl font-bold text-slate-950 dark:text-white">Dashboard</h1>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${TONS_BADGE[executiveStatus.tone] || TONS_BADGE.neutro}`}
              title={executiveStatus.description}
            >
              <StatusIcon className="h-3.5 w-3.5" aria-hidden="true" />
              {executiveStatus.title}
            </span>
            {lastUpdate && (
              <span className="text-xs text-slate-400">
                Atualizado às{" "}
                {lastUpdate.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <SeletorOpcoes
              rotulo="Período"
              opcoes={PERIOD_OPTIONS}
              valorSelecionado={periodDays}
              aoSelecionar={setPeriodDays}
            />
            <BotaoInteracao
              icon={HelpCircle}
              tamanho="pequeno"
              onClick={iniciarTour}
              title="Conhecer o dashboard"
              aria-label="Conhecer o dashboard"
            >
              <span className="hidden sm:inline">Entender painel</span>
            </BotaoInteracao>
            <BotaoInteracao icon={MessageCircle} tamanho="normal" onClick={openManagementAssistant}>
              Analisar com IA
            </BotaoInteracao>
            <BotaoInteracao
              icon={RefreshCw}
              tamanho="pequeno"
              loading={refreshing}
              onClick={loadDashboard}
            >
              Atualizar
            </BotaoInteracao>
          </div>
        </div>
      </section>

      {failedBlocks.length > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>
            Parte do painel não pôde ser atualizada ({failedBlocks.join(", ")}). Os demais números
            continuam disponíveis.
          </p>
        </div>
      )}

      <section id="tour-stats">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Resultado do período
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">{periodLabel}</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <CartaoIndicador
            icone={TrendingUp}
            tom="informativo"
            titulo={porRecebimento ? "Recebimentos de vendas" : "Faturamento"}
            detalhe={periodLabel}
            aoClicar={() => navigate(getDashboardDetailPath("sales", periodDays))}
          >
            <p className="text-2xl font-bold leading-tight text-slate-950 dark:text-white">
              {formatMoneyBRL(commercialValue)}
            </p>
          </CartaoIndicador>
          <CartaoIndicador
            icone={ShoppingBag}
            tom="neutro"
            titulo="Pedidos / unidades"
            detalhe={
              porRecebimento ? "Vendas e itens pela data da venda" : "Vendas e itens movimentados"
            }
            aoClicar={() => navigate(getDashboardDetailPath("sales", periodDays))}
          >
            <p className="text-2xl font-bold leading-tight text-slate-950 dark:text-white">
              {formatQuantity(salesCount)} / {formatQuantity(unitsSold)}
            </p>
          </CartaoIndicador>
          <CartaoIndicador
            icone={BarChart3}
            tom={salesProfit >= 0 ? "sucesso" : "perigo"}
            titulo="Lucro das vendas"
            detalhe="Após custos e deduções de cada venda"
            aoClicar={() => navigate("/financeiro/dre")}
          >
            <p className="text-2xl font-bold leading-tight text-slate-950 dark:text-white">
              {formatMoneyBRL(salesProfit)}
            </p>
          </CartaoIndicador>
        </div>
      </section>

      <section id="tour-financeiro" className="space-y-4">
        <div>
          <div className="mb-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Posição financeira</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Os números essenciais para saber onde a empresa está agora
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            <CartaoIndicador
              icone={Building2}
              tom="informativo"
              titulo={bankBalance === null ? "Saldo estimado" : "Saldo em bancos"}
              detalhe="Disponibilidade atual"
              aoClicar={() => navigate("/financeiro/bancos")}
            >
              <p className="text-lg font-bold leading-tight text-slate-950 dark:text-white">
                {formatMoneyBRL(displayedBalance)}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              icone={cashResult >= 0 ? TrendingUp : TrendingDown}
              tom={cashResult >= 0 ? "sucesso" : "perigo"}
              titulo="Resultado de caixa"
              detalhe={`${formatMoneyBRL(indicators.inflows)} entrou · ${formatMoneyBRL(indicators.outflows)} saiu`}
              aoClicar={() => navigate(getDashboardDetailPath("cashFlow", periodDays))}
            >
              <p className="text-lg font-bold leading-tight text-slate-950 dark:text-white">
                {formatMoneyBRL(cashResult)}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              icone={BarChart3}
              tom="neutro"
              titulo="Ticket médio"
              detalhe={periodLabel}
              aoClicar={() => navigate(getDashboardDetailPath("sales", periodDays))}
            >
              <p className="text-lg font-bold leading-tight text-slate-950 dark:text-white">
                {formatMoneyBRL(summary?.vendas_periodo?.ticket_medio || 0)}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              icone={TrendingUp}
              tom="sucesso"
              titulo="Total a receber"
              detalhe="Valores ainda em aberto"
              aoClicar={() => navigate(getDashboardDetailPath("receivableOpen", periodDays))}
            >
              <p className="text-lg font-bold leading-tight text-slate-950 dark:text-white">
                {formatMoneyBRL(summary?.contas_receber?.total || 0)}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              icone={TrendingDown}
              tom="perigo"
              titulo="Total a pagar"
              detalhe="Compromissos ainda em aberto"
              aoClicar={() => navigate(getDashboardDetailPath("payableOpen", periodDays))}
            >
              <p className="text-lg font-bold leading-tight text-slate-950 dark:text-white">
                {formatMoneyBRL(summary?.contas_pagar?.total || 0)}
              </p>
            </CartaoIndicador>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Atenção agora</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              O que está atrasado, vence hoje ou merece acompanhamento
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            <CartaoIndicador
              icone={WalletCards}
              tom={indicators.overdueReceivable > 0 ? "atencao" : "sucesso"}
              titulo="Recebimentos vencidos"
              detalhe={
                indicators.overdueReceivable > 0
                  ? "Priorize as cobranças mais antigas"
                  : "Nenhum valor vencido"
              }
              aoClicar={() => navigate(getDashboardDetailPath("receivableOverdue", periodDays))}
            >
              <p className="text-xl font-bold text-slate-900 dark:text-white">
                {formatMoneyBRL(indicators.overdueReceivable)}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              icone={Clock3}
              tom={indicators.overduePayable > 0 ? "atencao" : "sucesso"}
              titulo="Pagamentos vencidos"
              detalhe={
                indicators.overduePayable > 0
                  ? "Revise juros e fornecedores prioritários"
                  : "Nenhum valor vencido"
              }
              aoClicar={() => navigate(getDashboardDetailPath("payableOverdue", periodDays))}
            >
              <p className="text-xl font-bold text-slate-900 dark:text-white">
                {formatMoneyBRL(indicators.overduePayable)}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              icone={Clock3}
              tom={indicators.dueTodayPayable > 0 ? "atencao" : "sucesso"}
              titulo="Pagamentos que vencem hoje"
              detalhe={
                indicators.dueTodayReceivable > 0
                  ? `${formatMoneyBRL(indicators.dueTodayReceivable)} a receber hoje`
                  : "Compromissos do dia, sem marcar como atraso"
              }
              aoClicar={() => navigate(getDashboardDetailPath("payableDueToday", periodDays))}
            >
              <p className="text-xl font-bold text-slate-900 dark:text-white">
                {formatMoneyBRL(indicators.dueTodayPayable)}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              icone={Users}
              tom={Number(management?.vips_inativos?.quantidade || 0) > 0 ? "atencao" : "sucesso"}
              titulo="VIPs em risco"
              detalhe={
                management?.vips_inativos?.quantidade > 0
                  ? `${management.vips_inativos.impacto} em impacto estimado`
                  : "Nenhum VIP inativo há mais de 20 dias"
              }
              aoClicar={() => navigate(getDashboardDetailPath("vipAtRisk", periodDays))}
            >
              <p className="text-xl font-bold text-slate-900 dark:text-white">
                {String(management?.vips_inativos?.quantidade || 0)}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              icone={Users}
              tom={
                Number(management?.clientes_inativos?.quantidade || 0) > 0 ? "atencao" : "sucesso"
              }
              titulo="Clientes inativos"
              detalhe={
                management?.clientes_inativos?.quantidade > 0
                  ? "Sem compra há mais de 90 dias"
                  : "Nenhum cliente nessa condição"
              }
              aoClicar={() => navigate(getDashboardDetailPath("inactiveCustomers", periodDays))}
            >
              <p className="text-xl font-bold text-slate-900 dark:text-white">
                {String(management?.clientes_inativos?.quantidade || 0)}
              </p>
            </CartaoIndicador>
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
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
                <XAxis
                  dataKey="data"
                  tickFormatter={formatDate}
                  tick={{ fill: chartTickColor, fontSize: 11 }}
                />
                <YAxis
                  width={54}
                  tickFormatter={(value) =>
                    Number(value).toLocaleString("pt-BR", { notation: "compact" })
                  }
                  tick={{ fill: chartTickColor, fontSize: 11 }}
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
            <div className="h-[260px]">
              <EstadoVazio
                icone={BarChart3}
                titulo="Sem movimento neste período"
                descricao="Escolha outro período ou registre novas movimentações."
              />
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
            <BotaoLink onClick={() => navigate("/produtos")}>Ver produtos</BotaoLink>
          </div>
          {topProducts.length > 0 ? (
            <ol className="space-y-2">
              {topProducts.map((product, index) => (
                <li
                  key={`${product.nome}-${index}`}
                  className="flex items-center gap-3 rounded-xl border border-slate-100 p-3 dark:border-slate-800"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-sm font-bold text-cyan-800 dark:bg-cyan-500/10 dark:text-cyan-300">
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
            <div className="min-h-56">
              <EstadoVazio icone={ShoppingBag} titulo="Sem produtos vendidos no período" />
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
              {
                label: "Clientes ativos",
                value: management?.total_clientes || 0,
                path: getDashboardDetailPath("activeCustomers", periodDays),
              },
              {
                label: "Novos promissores",
                value: management?.oportunidades_novos?.quantidade || 0,
                path: getDashboardDetailPath("promisingCustomers", periodDays),
              },
              {
                label: "Sem WhatsApp",
                value: management?.whatsapp_inativo?.quantidade || 0,
                path: getDashboardDetailPath("customersWithoutWhatsapp", periodDays),
              },
            ].map(({ label, value, path }) => (
              <button
                key={label}
                type="button"
                onClick={() => navigate(path)}
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
                  path: getDashboardDetailPath("receivableOverdue", periodDays),
                  tone: "text-emerald-700 dark:text-emerald-300",
                },
                {
                  key: "contas_pagar",
                  label: "A pagar",
                  personKey: "fornecedor",
                  path: getDashboardDetailPath("payableOverdue", periodDays),
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
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
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
                <CheckCircle2 className="mx-auto h-7 w-7 text-emerald-600" aria-hidden="true" />
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
