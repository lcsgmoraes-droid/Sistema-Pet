import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Calculator,
  DollarSign,
  RefreshCcw,
  ShoppingCart,
  Target,
  TrendingUp,
} from "lucide-react";
import api from "../api";
import { formatMoneyBRL, formatPercent } from "../utils/formatters";
import { calcularImpactoPontoEquilibrio } from "./pontoEquilibrioImpactoUtils";

function formatarDataInput(data) {
  const local = new Date(data.getTime() - data.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function inicioMesAtual() {
  const hoje = new Date();
  return formatarDataInput(new Date(hoje.getFullYear(), hoje.getMonth(), 1));
}

function fimMesAtual() {
  const hoje = new Date();
  return formatarDataInput(new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0));
}

function MetricCard({ title, value, subtitle, tone = "slate", icon: Icon }) {
  const tones = {
    slate: "border-slate-200 bg-white text-slate-900",
    green: "border-emerald-200 bg-emerald-50 text-emerald-900",
    blue: "border-blue-200 bg-blue-50 text-blue-900",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    red: "border-red-200 bg-red-50 text-red-900",
  };

  return (
    <div className={`rounded-lg border p-4 ${tones[tone] || tones.slate}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">{title}</p>
          <p className="mt-2 text-2xl font-bold">{value}</p>
          {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
        </div>
        {Icon && <Icon className="h-5 w-5 text-current opacity-70" />}
      </div>
    </div>
  );
}

function formatarDataBR(data) {
  if (!data) return "-";
  const [ano, mes, dia] = String(data).split("T")[0].split("-");
  if (!ano || !mes || !dia) return data;
  return `${dia}/${mes}/${ano}`;
}

function DetalheContasCard({ title, total, items = [], tone = "slate", emptyLabel = "Nenhum lancamento" }) {
  const tones = {
    slate: "border-slate-200",
    amber: "border-amber-200",
    blue: "border-blue-200",
    red: "border-red-200",
  };

  return (
    <div className={`rounded-lg border bg-white p-4 ${tones[tone] || tones.slate}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-900">{title}</h3>
          <p className="text-xs text-slate-500">Origem dos valores usados no calculo</p>
        </div>
        <span className="text-sm font-bold text-slate-900">{formatMoneyBRL(total || 0)}</span>
      </div>

      <div className="mt-3 max-h-72 overflow-y-auto divide-y divide-slate-100">
        {items.length === 0 ? (
          <p className="py-4 text-sm text-slate-500">{emptyLabel}</p>
        ) : (
          items.map((item) => (
            <div key={`${title}-${item.id}`} className="py-3 text-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-semibold text-slate-900" title={item.descricao}>
                    #{item.id} {item.descricao}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {formatarDataBR(item.data_vencimento)}
                    {item.fornecedor_nome ? ` | ${item.fornecedor_nome}` : ""}
                  </p>
                  <p className="mt-1 text-xs text-blue-700">{item.origem_classificacao}</p>
                </div>
                <span className="shrink-0 font-bold text-slate-900">{formatMoneyBRL(item.valor || 0)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

const CANAIS = [
  { value: "", label: "Todos os canais" },
  { value: "loja_fisica", label: "Loja fisica" },
  { value: "mercado_livre", label: "Mercado Livre" },
  { value: "shopee", label: "Shopee" },
  { value: "amazon", label: "Amazon" },
  { value: "site", label: "Site" },
];

const CENARIOS_RAPIDOS = [
  { descricao: "Aumento aluguel", valor: "1000" },
  { descricao: "Novo funcionario", valor: "3000" },
  { descricao: "Reducao de custo", valor: "-500" },
];

function formatarImpactoMoeda(valor) {
  if (valor == null) return "-";
  if (valor > 0) return `+ ${formatMoneyBRL(valor)}`;
  if (valor < 0) return `- ${formatMoneyBRL(Math.abs(valor))}`;
  return formatMoneyBRL(0);
}

function formatarImpactoVendas(valor) {
  if (valor == null) return "-";
  if (valor > 0) return `+${valor}`;
  return String(valor);
}

export default function PontoEquilibrio() {
  const [filtros, setFiltros] = useState({
    data_inicio: inicioMesAtual(),
    data_fim: fimMesAtual(),
    canal: "",
  });
  const [impactoForm, setImpactoForm] = useState({
    descricao: "",
    valor: "",
  });
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");

  const percentualAtingido = Math.min(Number(dados?.percentual_atingido || 0), 100);
  const impactoValor = Number(impactoForm.valor || 0);
  const impactoSimulado = useMemo(() => {
    if (!dados) return null;
    return calcularImpactoPontoEquilibrio({
      despesasFixas: dados.despesas_fixas,
      pontoEquilibrio: dados.ponto_equilibrio,
      margemContribuicaoPercentual: dados.margem_contribuicao_percentual,
      faturamento: dados.faturamento,
      ticketMedio: dados.ticket_medio,
      impactoCustoFixo: impactoValor,
    });
  }, [dados, impactoValor]);

  const statusResumo = useMemo(() => {
    if (!dados) return null;
    if (dados.status === "atingido") {
      return {
        tone: "green",
        title: "Ponto de Equilibrio atingido",
        text: `A empresa ja faturou ${formatMoneyBRL(dados.faturamento)} no periodo e passou do minimo estimado.`,
      };
    }
    if (dados.status === "nao_atingido") {
      return {
        tone: "amber",
        title: "Ainda falta faturar",
        text: `Faltam ${formatMoneyBRL(dados.falta_faturar || 0)} para cobrir os custos fixos pela margem atual.`,
      };
    }
    if (dados.status === "margem_insuficiente") {
      return {
        tone: "red",
        title: "Margem insuficiente",
        text: "O faturamento existe, mas os custos variaveis estao consumindo a margem de contribuicao.",
      };
    }
    return {
      tone: "slate",
      title: "Sem faturamento no periodo",
      text: "Selecione um periodo com vendas finalizadas para calcular a margem.",
    };
  }, [dados]);

  const carregarDados = async () => {
    setLoading(true);
    setErro("");
    try {
      const params = new URLSearchParams({
        data_inicio: filtros.data_inicio,
        data_fim: filtros.data_fim,
      });
      if (filtros.canal) {
        params.append("canais", filtros.canal);
      }
      const response = await api.get(`/financeiro/ponto-equilibrio?${params.toString()}`);
      setDados(response.data);
    } catch (error) {
      console.error("Erro ao carregar ponto de equilibrio:", error);
      setErro(error.response?.data?.detail || "Nao foi possivel carregar o ponto de equilibrio.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarDados();
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-blue-100 p-3 text-blue-700">
                <Calculator className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Ponto de Equilibrio</h1>
                <p className="text-sm text-slate-600">
                  Quanto precisa vender para empatar os custos fixos pela margem de contribuicao atual.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-3 md:grid-cols-[160px_160px_180px_auto]">
            <div>
              <label className="text-xs font-semibold text-slate-600">Inicio</label>
              <input
                type="date"
                value={filtros.data_inicio}
                onChange={(event) => setFiltros({ ...filtros, data_inicio: event.target.value })}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Fim</label>
              <input
                type="date"
                value={filtros.data_fim}
                onChange={(event) => setFiltros({ ...filtros, data_fim: event.target.value })}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Canal</label>
              <select
                value={filtros.canal}
                onChange={(event) => setFiltros({ ...filtros, canal: event.target.value })}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                {CANAIS.map((canal) => (
                  <option key={canal.value || "todos"} value={canal.value}>
                    {canal.label}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={carregarDados}
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:bg-slate-300"
            >
              <RefreshCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Atualizar
            </button>
          </div>
        </div>

        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
          <p className="font-semibold">Formula usada</p>
          <p className="mt-1">
            Ponto de equilibrio = custos fixos / margem de contribuicao. A margem de contribuicao
            considera faturamento menos CMV estimado e despesas variaveis operacionais. Compras de
            estoque/produtos para revenda ficam fora das despesas variaveis para nao duplicar o CMV.
          </p>
        </div>

        {erro && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {erro}
          </div>
        )}

        {dados && statusResumo && (
          <>
            <div className={`rounded-lg border p-4 ${
              statusResumo.tone === "green"
                ? "border-emerald-200 bg-emerald-50"
                : statusResumo.tone === "amber"
                  ? "border-amber-200 bg-amber-50"
                  : statusResumo.tone === "red"
                    ? "border-red-200 bg-red-50"
                    : "border-slate-200 bg-white"
            }`}>
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-lg font-bold text-slate-900">{statusResumo.title}</p>
                  <p className="text-sm text-slate-700">{statusResumo.text}</p>
                </div>
                <div className="min-w-[220px]">
                  <div className="flex justify-between text-xs font-semibold text-slate-600">
                    <span>0%</span>
                    <span>{formatPercent(dados.percentual_atingido || 0)}</span>
                  </div>
                  <div className="mt-1 h-3 overflow-hidden rounded-full bg-white/80">
                    <div
                      className="h-full rounded-full bg-emerald-500 transition-all"
                      style={{ width: `${percentualAtingido}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                icon={Target}
                title="Ponto minimo"
                value={dados.ponto_equilibrio == null ? "Indefinido" : formatMoneyBRL(dados.ponto_equilibrio)}
                subtitle="Faturamento necessario para empatar"
                tone={dados.status === "atingido" ? "green" : "amber"}
              />
              <MetricCard
                icon={DollarSign}
                title="Faturamento"
                value={formatMoneyBRL(dados.faturamento)}
                subtitle={`${dados.quantidade_vendas || 0} venda(s) no periodo`}
                tone="blue"
              />
              <MetricCard
                icon={TrendingUp}
                title="Margem de contribuicao"
                value={formatPercent(dados.margem_contribuicao_percentual)}
                subtitle={formatMoneyBRL(dados.margem_contribuicao)}
                tone={dados.margem_contribuicao_percentual > 0 ? "green" : "red"}
              />
              <MetricCard
                icon={ShoppingCart}
                title="Vendas necessarias"
                value={dados.vendas_necessarias == null ? "-" : String(dados.vendas_necessarias)}
                subtitle={`Ticket medio ${formatMoneyBRL(dados.ticket_medio)}`}
                tone="slate"
              />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <h2 className="text-base font-semibold text-slate-900">Composicao da margem</h2>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">Faturamento</span>
                    <span className="font-semibold text-slate-900">{formatMoneyBRL(dados.faturamento)}</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">CMV estimado</span>
                    <span className="font-semibold text-red-700">- {formatMoneyBRL(dados.cmv_estimado)}</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">Despesas variaveis</span>
                    <span className="font-semibold text-red-700">- {formatMoneyBRL(dados.despesas_variaveis)}</span>
                  </div>
                  <div className="border-t border-slate-100 pt-3">
                    <div className="flex justify-between gap-4">
                      <span className="font-semibold text-slate-700">Margem de contribuicao</span>
                      <span className="font-bold text-emerald-700">{formatMoneyBRL(dados.margem_contribuicao)}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <h2 className="text-base font-semibold text-slate-900">Base de custos fixos</h2>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">Custos fixos classificados</span>
                    <span className="font-semibold text-slate-900">{formatMoneyBRL(dados.despesas_fixas)}</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">Custos variaveis totais</span>
                    <span className="font-semibold text-slate-900">{formatMoneyBRL(dados.custos_variaveis)}</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">Sem classificacao para PE</span>
                    <span className="font-semibold text-amber-700">
                      {formatMoneyBRL(dados.despesas_sem_classificacao)}
                    </span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">Fora do PE: compras de estoque</span>
                    <span className="font-semibold text-slate-700">
                      {formatMoneyBRL(dados.despesas_estoque_excluidas || 0)}
                    </span>
                  </div>
                  <p className="rounded-md bg-slate-50 p-3 text-xs text-slate-600">
                    A base usa contas a pagar para os valores reais, DRE para a classificacao
                    gerencial e provisoes, e complementa a folha pelos funcionarios ativos quando
                    ainda nao houver lancamento suficiente. Compras de produto para revenda ficam
                    separadas porque o custo entra pelo CMV quando o produto e vendido.
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-indigo-200 bg-white p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Calculadora de impacto</h2>
                  <p className="mt-1 text-sm text-slate-600">
                    Simule aumento ou reducao mensal no custo fixo usando a margem e o ticket medio atuais.
                  </p>
                </div>
                <span className="w-fit rounded-md bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
                  Simulador
                </span>
              </div>

              <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(220px,1fr)_220px]">
                <div>
                  <label className="text-xs font-semibold text-slate-600">Descricao do cenario</label>
                  <input
                    type="text"
                    value={impactoForm.descricao}
                    onChange={(event) => setImpactoForm({ ...impactoForm, descricao: event.target.value })}
                    placeholder="Ex: aumento aluguel, novo funcionario"
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-600">Impacto mensal no custo fixo</label>
                  <input
                    type="number"
                    step="0.01"
                    value={impactoForm.valor}
                    onChange={(event) => setImpactoForm({ ...impactoForm, valor: event.target.value })}
                    placeholder="Ex: 3000 ou -800"
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {CENARIOS_RAPIDOS.map((cenario) => (
                  <button
                    key={cenario.descricao}
                    type="button"
                    onClick={() => setImpactoForm(cenario)}
                    className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 transition-colors hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
                  >
                    {cenario.descricao} {formatarImpactoMoeda(Number(cenario.valor))}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setImpactoForm({ descricao: "", valor: "" })}
                  className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-50"
                >
                  Limpar
                </button>
              </div>

              {impactoSimulado?.calculavel ? (
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-md bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase text-slate-500">Novo custo fixo</p>
                    <p className="mt-1 text-xl font-bold text-slate-900">
                      {formatMoneyBRL(impactoSimulado.novoCustoFixo)}
                    </p>
                    <p className={impactoValor >= 0 ? "mt-1 text-xs text-red-700" : "mt-1 text-xs text-emerald-700"}>
                      {formatarImpactoMoeda(impactoSimulado.impactoRealCustoFixo)}
                    </p>
                  </div>
                  <div className="rounded-md bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase text-slate-500">Novo ponto minimo</p>
                    <p className="mt-1 text-xl font-bold text-slate-900">
                      {formatMoneyBRL(impactoSimulado.novoPontoEquilibrio)}
                    </p>
                    <p
                      className={
                        impactoSimulado.impactoPontoEquilibrio >= 0
                          ? "mt-1 text-xs text-red-700"
                          : "mt-1 text-xs text-emerald-700"
                      }
                    >
                      {formatarImpactoMoeda(impactoSimulado.impactoPontoEquilibrio)}
                    </p>
                  </div>
                  <div className="rounded-md bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase text-slate-500">Vendas a mais/menos</p>
                    <p className="mt-1 text-xl font-bold text-slate-900">
                      {formatarImpactoVendas(impactoSimulado.vendasImpacto)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">Pelo ticket medio atual</p>
                  </div>
                  <div className="rounded-md bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase text-slate-500">Falta/sobra projetada</p>
                    <p
                      className={
                        impactoSimulado.saldoAposSimulacao >= 0
                          ? "mt-1 text-xl font-bold text-emerald-700"
                          : "mt-1 text-xl font-bold text-red-700"
                      }
                    >
                      {impactoSimulado.saldoAposSimulacao >= 0
                        ? formatMoneyBRL(impactoSimulado.saldoAposSimulacao)
                        : formatarImpactoMoeda(impactoSimulado.saldoAposSimulacao)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {impactoSimulado.saldoAposSimulacao >= 0 ? "Acima do ponto minimo" : "Ainda falta faturar"}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  A simulacao depende de margem de contribuicao positiva no periodo selecionado.
                </div>
              )}
            </div>

            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <h2 className="text-base font-semibold text-slate-900">Origem dos valores</h2>
              <p className="mt-1 text-sm text-slate-600">
                Use esta abertura para conferir o que entrou como despesa fixa, despesa variavel,
                sem classificacao ou fora do ponto de equilibrio.
              </p>
              <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
                <DetalheContasCard
                  title="Despesas fixas"
                  total={dados.despesas_fixas}
                  items={dados.detalhes_classificacao?.fixas || []}
                  tone="amber"
                />
                <DetalheContasCard
                  title="Despesas variaveis"
                  total={dados.despesas_variaveis}
                  items={dados.detalhes_classificacao?.variaveis || []}
                  tone="blue"
                />
                <DetalheContasCard
                  title="Sem classificacao"
                  total={dados.despesas_sem_classificacao}
                  items={dados.detalhes_classificacao?.sem_classificacao || []}
                  tone="red"
                />
                <DetalheContasCard
                  title="Fora do PE"
                  total={dados.despesas_estoque_excluidas}
                  items={dados.detalhes_classificacao?.estoque_excluido || []}
                  tone="slate"
                  emptyLabel="Nenhuma compra de estoque identificada"
                />
              </div>
            </div>

            {(dados.produtos_sem_custo > 0 || dados.quantidade_contas_sem_classificacao > 0) && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="mt-0.5 h-5 w-5" />
                  <div>
                    <p className="font-semibold">Atencao na precisao do calculo</p>
                    <p className="mt-1">
                      {dados.produtos_sem_custo > 0 && `${dados.produtos_sem_custo} produto(s) vendido(s) estao sem custo cadastrado. `}
                      {dados.quantidade_contas_sem_classificacao > 0 && `${dados.quantidade_contas_sem_classificacao} conta(s) a pagar estao sem classificacao fixo/variavel. `}
                      Esses pontos podem subestimar ou superestimar o ponto de equilibrio.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
