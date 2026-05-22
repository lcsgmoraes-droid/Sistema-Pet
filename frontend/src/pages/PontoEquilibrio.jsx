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

function formatarDataInput(data) {
  const local = new Date(data.getTime() - data.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function inicioMesAtual() {
  const hoje = new Date();
  return formatarDataInput(new Date(hoje.getFullYear(), hoje.getMonth(), 1));
}

function hojeInput() {
  return formatarDataInput(new Date());
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

const CANAIS = [
  { value: "", label: "Todos os canais" },
  { value: "loja_fisica", label: "Loja fisica" },
  { value: "mercado_livre", label: "Mercado Livre" },
  { value: "shopee", label: "Shopee" },
  { value: "amazon", label: "Amazon" },
  { value: "site", label: "Site" },
];

export default function PontoEquilibrio() {
  const [filtros, setFiltros] = useState({
    data_inicio: inicioMesAtual(),
    data_fim: hojeInput(),
    canal: "",
  });
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");

  const percentualAtingido = Math.min(Number(dados?.percentual_atingido || 0), 100);

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
            considera faturamento menos CMV estimado e despesas variaveis.
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
                  <p className="rounded-md bg-slate-50 p-3 text-xs text-slate-600">
                    Para melhorar a precisao, classifique as contas a pagar em tipo de despesa
                    fixo/variavel ou marque o campo de PE na subcategoria DRE.
                  </p>
                </div>
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
