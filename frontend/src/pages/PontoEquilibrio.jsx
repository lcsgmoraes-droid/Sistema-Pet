import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  Calculator,
  DollarSign,
  RefreshCcw,
  ShoppingCart,
  Target,
  TrendingUp,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart as RePieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../api";
import ModuleTabs from "../components/ui/ModuleTabs";
import { formatMoneyBRL, formatPercent } from "../utils/formatters";
import {
  FAIXAS_PORTE_PETSHOP,
  calcularImpactoPontoEquilibrio,
  montarAnaliseCustosPontoEquilibrio,
} from "./pontoEquilibrioImpactoUtils";

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

const LINHAS_CLASSIFICACAO_PE = [
  {
    id: "fixas",
    label: "Despesas fixas",
    tipo: "custo",
    valorKey: "despesas_fixas",
    origem: "Contas a pagar, DRE e folha gerencial",
  },
  {
    id: "variaveis",
    label: "Outros custos variaveis",
    tipo: "deducao",
    valorKey: "outros_variaveis",
    origem: "Contas/DRE fora do snapshot da venda",
  },
  {
    id: "custos_venda_snapshot",
    label: "Custos de venda ja no snapshot",
    tipo: "informativo",
    valorKey: "despesas_variaveis_ja_cobertas",
    origem: "Separados para nao duplicar custos",
  },
  {
    id: "sem_classificacao",
    label: "Sem classificacao",
    tipo: "alerta",
    valorKey: "despesas_sem_classificacao",
    origem: "Contas que precisam de classificacao",
  },
  {
    id: "estoque_excluido",
    label: "Fora do PE",
    tipo: "informativo",
    valorKey: "despesas_estoque_excluidas",
    origem: "Compra de estoque entra via CMV",
  },
];

function linhaValorClassName(tipo) {
  if (tipo === "receita") return "text-emerald-700";
  if (tipo === "alerta") return "text-amber-700";
  if (tipo === "informativo") return "text-slate-700";
  return "text-red-700";
}

function montarLinhasDetalhamentoPontoEquilibrio(dados) {
  const subtotais = dados?.detalhes_margem?.subtotais || [];
  const linhasMargem = subtotais
    .filter((subtotal) => Math.abs(Number(subtotal.valor || 0)) > 0 || subtotal.id === "custo_fiscal")
    .map((subtotal) => ({
      ...subtotal,
      grupo: subtotal.id,
      origem: "Snapshot financeiro das vendas",
    }));

  const linhasClassificacao = LINHAS_CLASSIFICACAO_PE.map((linha) => ({
    ...linha,
    grupo: linha.id,
    valor: Number(dados?.[linha.valorKey] || 0),
  })).filter((linha) => Math.abs(Number(linha.valor || 0)) > 0 || linha.id === "sem_classificacao");

  return [...linhasMargem, ...linhasClassificacao];
}

function DetalhamentoMargemPanel({ dados, onAbrirDetalhes }) {
  const linhas = montarLinhasDetalhamentoPontoEquilibrio(dados);

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
        <h2 className="text-base font-semibold text-blue-950">Detalhamento da margem e custos</h2>
        <p className="mt-1 text-sm text-blue-900">
          Clique em detalhes para carregar os lancamentos daquela linha. O resumo fica leve e os
          itens completos aparecem sob demanda, no mesmo estilo da DRE.
        </p>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="grid grid-cols-1 gap-1 bg-slate-50 px-4 py-3 text-xs font-bold uppercase text-slate-500 sm:grid-cols-[minmax(220px,1fr)_160px_130px]">
          <span>Origem das contas e custos fixos</span>
          <span className="sm:text-right">Valor</span>
          <span className="sm:text-right">Acao</span>
        </div>
        <div className="divide-y divide-slate-100">
          {linhas.map((linha) => (
            <button
              key={linha.grupo}
              type="button"
              onClick={() => onAbrirDetalhes(linha)}
              className="grid w-full grid-cols-1 items-center gap-2 px-4 py-3 text-left text-sm transition-colors hover:bg-blue-50 sm:grid-cols-[minmax(220px,1fr)_160px_130px] sm:gap-3"
            >
              <span className="min-w-0">
                <span className="block font-semibold text-slate-900">{linha.label}</span>
                <span className="block truncate text-xs text-slate-500">{linha.origem}</span>
              </span>
              <span className={`font-bold sm:text-right ${linhaValorClassName(linha.tipo)}`}>
                {linha.tipo === "receita" ? "+" : linha.tipo === "informativo" ? "" : "-"} {formatMoneyBRL(Math.abs(linha.valor || 0))}
              </span>
              <span className="sm:text-right">
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                  detalhes
                </span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function DetalhesPontoEquilibrioDrawer({ linha, detalhes, loading, onClose, onPageChange }) {
  if (!linha) return null;

  const items = detalhes?.items || [];
  return (
    <div className="fixed inset-0 z-[70] bg-slate-900/30" onClick={onClose}>
      <aside
        className="fixed inset-x-0 bottom-0 max-h-[86dvh] overflow-hidden rounded-t-2xl bg-white shadow-2xl md:inset-y-0 md:left-auto md:right-0 md:max-h-none md:w-[760px] md:rounded-none"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex h-full flex-col">
          <div className="border-b border-slate-200 p-4 md:p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase text-slate-500">Lancamentos do ponto de equilibrio</p>
                <h2 className="mt-1 text-lg font-bold text-slate-900 md:text-xl">{detalhes?.label || linha.label}</h2>
                <p className="mt-1 text-sm text-slate-600">{detalhes?.periodo || "Periodo filtrado"}</p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-md p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
                aria-label="Fechar detalhes"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-semibold uppercase text-slate-500">Total da linha</p>
                <p className="mt-1 text-lg font-bold text-slate-900">{formatMoneyBRL(detalhes?.total ?? linha.valor ?? 0)}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-semibold uppercase text-slate-500">Lancamentos</p>
                <p className="mt-1 text-lg font-bold text-slate-900">{detalhes?.total_itens ?? "-"}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-semibold uppercase text-slate-500">Origem</p>
                <p className="mt-1 text-sm font-semibold text-slate-800">{items[0]?.origem_label || linha.origem}</p>
              </div>
            </div>
            {detalhes?.origem && (
              <p className="mt-3 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800">{detalhes.origem}</p>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4 md:p-5">
            {loading ? (
              <div className="flex h-48 items-center justify-center text-slate-500">
                <RefreshCcw className="mr-2 h-4 w-4 animate-spin" />
                Carregando lancamentos...
              </div>
            ) : items.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
                Nenhum lancamento encontrado para esta linha no periodo.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <div className="grid min-w-[460px] grid-cols-[110px_minmax(220px,1fr)_120px] bg-slate-50 px-3 py-2 text-xs font-bold uppercase text-slate-500">
                  <span>Data</span>
                  <span>Descricao</span>
                  <span className="text-right">Valor</span>
                </div>
                <div className="divide-y divide-slate-100 bg-white">
                  {items.map((item, index) => (
                    <div key={item.id || `${linha.grupo}-${index}`} className="grid min-w-[460px] grid-cols-[110px_minmax(220px,1fr)_120px] gap-3 px-3 py-3 text-sm">
                      <span className="text-slate-600">{formatarDataBR(item.data)}</span>
                      <span className="min-w-0">
                        <span className="block truncate font-semibold text-slate-900" title={item.descricao}>
                          {item.descricao}
                        </span>
                        {(item.contraparte || item.observacao || item.origem_classificacao) && (
                          <span className="mt-1 block truncate text-xs text-slate-500">
                            {item.contraparte || item.observacao || item.origem_classificacao}
                          </span>
                        )}
                      </span>
                      <span className="text-right font-bold text-slate-900">{formatMoneyBRL(item.valor || 0)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {detalhes && detalhes.pages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-200 p-4 text-sm">
              <button
                type="button"
                disabled={loading || detalhes.page <= 1}
                onClick={() => onPageChange(detalhes.page - 1)}
                className="rounded-md border border-slate-200 px-3 py-2 font-semibold text-slate-700 disabled:opacity-50"
              >
                Anterior
              </button>
              <span className="text-slate-600">Pagina {detalhes.page} de {detalhes.pages}</span>
              <button
                type="button"
                disabled={loading || detalhes.page >= detalhes.pages}
                onClick={() => onPageChange(detalhes.page + 1)}
                className="rounded-md border border-slate-200 px-3 py-2 font-semibold text-slate-700 disabled:opacity-50"
              >
                Proxima
              </button>
            </div>
          )}
        </div>
      </aside>
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

const MARGEM_PONTO_EQUILIBRIO_OPCOES = [
  { value: "media_12_meses_fechados", label: "Media 12 meses fechados" },
  { value: "media_6_meses_fechados", label: "Media 6 meses fechados" },
  { value: "media_3_meses_fechados", label: "Media 3 meses fechados" },
  { value: "mes_anterior_fechado", label: "Mes anterior fechado" },
  { value: "periodo_atual", label: "Periodo atual" },
];

const MODO_CUSTO_FISCAL_OPCOES = [
  { value: "gerencial_completo", label: "Visao gerencial completa" },
  { value: "documentos_emitidos", label: "Somente documentos emitidos" },
];

const CENARIOS_RAPIDOS = [
  { descricao: "Aumento aluguel", valor: "1000", faturamento: "" },
  { descricao: "Novo funcionario", valor: "3000", faturamento: "" },
  { descricao: "Reducao de custo", valor: "-500", faturamento: "" },
];

const ABAS_PONTO_EQUILIBRIO = [
  { id: "resumo", label: "Resumo" },
  { id: "detalhamento", label: "Detalhamento" },
  { id: "simulador", label: "Simulador" },
  { id: "graficos", label: "Graficos" },
];

const TOOLTIP_FAIXAS_PORTE =
  "Faixas gerenciais mensais: Pequeno ate R$ 80 mil/mes; Medio de R$ 80 mil a R$ 250 mil/mes; Grande acima de R$ 250 mil/mes. Use como parametro interno, nao como enquadramento fiscal.";

const CORES_GRAFICO_CUSTOS = ["#2563eb", "#059669", "#d97706", "#7c3aed", "#dc2626", "#0891b2", "#64748b"];
const PONTO_EQUILIBRIO_REQUEST_TIMEOUT_MS = 120000;

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

function formatarVariacaoPercentual(valor) {
  if (valor == null) return "-";
  if (valor > 0) return `+${formatPercent(valor)}`;
  return formatPercent(valor);
}

function TooltipMoeda({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-md border border-slate-200 bg-white p-2 text-xs shadow-sm">
      <p className="font-semibold text-slate-900">{label}</p>
      {payload.map((item) => (
        <p key={item.name} className="text-slate-600">
          {item.name}: {formatMoneyBRL(item.value)}
        </p>
      ))}
    </div>
  );
}

function TooltipPercentual({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-md border border-slate-200 bg-white p-2 text-xs shadow-sm">
      <p className="font-semibold text-slate-900">{label}</p>
      {payload.map((item) => (
        <p key={item.name} className="text-slate-600">
          {item.name}: {formatPercent(item.value)}
        </p>
      ))}
    </div>
  );
}

function statusParecerClasses(status) {
  if (status === "saudavel") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "atencao") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-red-200 bg-red-50 text-red-800";
}

function statusParecerLabel(status) {
  if (status === "saudavel") return "Saudavel";
  if (status === "atencao") return "Atencao";
  return "Acima do ideal";
}

function statusParecerLabelGerencial(parecer) {
  if (parecer.id === "total_fixo") return statusParecerLabel(parecer.status);
  if (parecer.status === "saudavel") return "Dentro da meta";
  if (parecer.status === "atencao") return "Pressiona total";
  return "Acima da referencia";
}

function SimuladorImpactoPanel({ dados, impactoForm, impactoSimulado, impactoValor, setImpactoForm }) {
  return (
    <div className="rounded-lg border border-indigo-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Calculadora de impacto</h2>
          <p className="mt-1 text-sm text-slate-600">
            Brinque com faturamento projetado e aumentos ou reducoes de custo fixo sem gravar nada.
          </p>
        </div>
        <span className="w-fit rounded-md bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
          Simulador
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(220px,1fr)_220px_220px]">
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
          <label className="text-xs font-semibold text-slate-600">Faturamento projetado</label>
          <input
            type="number"
            step="0.01"
            value={impactoForm.faturamento}
            onChange={(event) => setImpactoForm({ ...impactoForm, faturamento: event.target.value })}
            placeholder={formatMoneyBRL(dados.faturamento)}
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
            onClick={() => setImpactoForm((prev) => ({ ...prev, ...cenario }))}
            className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 transition-colors hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
          >
            {cenario.descricao} {formatarImpactoMoeda(Number(cenario.valor))}
          </button>
        ))}
        <button
          type="button"
          onClick={() => setImpactoForm({ descricao: "", valor: "", faturamento: "" })}
          className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-50"
        >
          Limpar
        </button>
      </div>

      {impactoSimulado?.calculavel ? (
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-md bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">Faturamento simulado</p>
            <p className="mt-1 text-xl font-bold text-slate-900">
              {formatMoneyBRL(impactoSimulado.faturamentoProjetado)}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Atual: {formatMoneyBRL(dados.faturamento)}
            </p>
          </div>
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
            <p className="text-xs font-semibold uppercase text-slate-500">Resultado projetado do mes</p>
            <p
              className={
                impactoSimulado.resultadoProjetado >= 0
                  ? "mt-1 text-xl font-bold text-emerald-700"
                  : "mt-1 text-xl font-bold text-red-700"
              }
            >
              {impactoSimulado.resultadoProjetado >= 0
                ? formatMoneyBRL(impactoSimulado.resultadoProjetado)
                : formatarImpactoMoeda(impactoSimulado.resultadoProjetado)}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Margem projetada {formatMoneyBRL(impactoSimulado.margemContribuicaoProjetada)}
            </p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">Vendas a mais/menos</p>
            <p className="mt-1 text-xl font-bold text-slate-900">
              {formatarImpactoVendas(impactoSimulado.vendasImpacto)}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Falta/sobra vs PE: {formatarImpactoMoeda(impactoSimulado.saldoAposSimulacao)}
            </p>
          </div>
        </div>
      ) : (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          A simulacao depende de margem de contribuicao positiva no periodo selecionado.
        </div>
      )}
    </div>
  );
}

function ParecerCard({ parecer }) {
  return (
    <div className={`rounded-lg border p-4 ${statusParecerClasses(parecer.status)}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-900">{parecer.titulo}</h3>
          <p className="mt-1 text-xs text-slate-600">{parecer.descricao}</p>
        </div>
        <span className="rounded-md bg-white/70 px-2 py-1 text-xs font-bold">
          {statusParecerLabelGerencial(parecer)}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Atual</p>
          <p className="font-bold text-slate-900">{formatPercent(parecer.percentualFaturamento)}</p>
          <p className="text-xs text-slate-600">{formatMoneyBRL(parecer.valor)}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Meta</p>
          <p className="font-bold text-slate-900">{formatPercent(parecer.metaPercentual)}</p>
          <p className={parecer.diferencaValor > 0 ? "text-xs text-red-700" : "text-xs text-emerald-700"}>
            {formatarVariacaoPercentual(parecer.diferencaPercentual)} ({formatarImpactoMoeda(parecer.diferencaValor)})
          </p>
          {parecer.id !== "total_fixo" && (
            <p className="mt-1 text-[11px] text-slate-500">
              Ref. setorial {formatPercent(parecer.referenciaPercentual)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function AnaliseCustosPanel({ analise, porteAnalise, setPorteAnalise }) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-blue-100 p-2 text-blue-700">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">Analise dos custos</h2>
              <p className="mt-1 text-sm text-slate-600">
                Parecer gerencial com metas setoriais ajustadas para caber no limite saudavel de custo fixo total.
                As referencias setoriais aparecem como contexto de comparacao.
              </p>
            </div>
          </div>

          <div className="w-full rounded-lg border border-slate-200 bg-slate-50 p-3 lg:w-72">
            <div className="flex items-center justify-between gap-2">
              <label className="text-xs font-semibold uppercase text-slate-600">Porte do petshop</label>
              <span
                title={TOOLTIP_FAIXAS_PORTE}
                className="cursor-help rounded-md bg-white px-2 py-1 text-[11px] font-semibold text-slate-600"
              >
                Faixas gerenciais mensais
              </span>
            </div>
            <select
              value={porteAnalise}
              onChange={(event) => setPorteAnalise(event.target.value)}
              className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              {FAIXAS_PORTE_PETSHOP.map((porte) => (
                <option key={porte.id} value={porte.id}>
                  {porte.label}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-600">
              {analise.porte.faixaMensal}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-bold text-slate-900">Composicao dos custos fixos</h3>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <RePieChart>
                <Pie
                  data={analise.grupos}
                  dataKey="valor"
                  nameKey="label"
                  innerRadius={62}
                  outerRadius={95}
                  paddingAngle={2}
                >
                  {analise.grupos.map((entry, index) => (
                    <Cell key={entry.id} fill={CORES_GRAFICO_CUSTOS[index % CORES_GRAFICO_CUSTOS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<TooltipMoeda />} />
              </RePieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-bold text-slate-900">% do faturamento vs meta</h3>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analise.comparativoPercentual} margin={{ left: -10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="nome" tick={{ fontSize: 11 }} interval={0} angle={-12} textAnchor="end" height={70} />
                <YAxis tickFormatter={(value) => `${value}%`} />
                <Tooltip content={<TooltipPercentual />} />
                <Bar dataKey="meta" name="Meta" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="atual" name="Atual" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {analise.pareceres.map((parecer) => (
          <ParecerCard key={parecer.id} parecer={parecer} />
        ))}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-bold text-slate-900">Ranking dos maiores custos fixos</h3>
        <div className="mt-3 divide-y divide-slate-100">
          {analise.grupos.map((grupo) => (
            <div key={grupo.id} className="flex items-center justify-between gap-4 py-3 text-sm">
              <div className="min-w-0">
                <p className="font-semibold text-slate-900">{grupo.label}</p>
                <p className="text-xs text-slate-500">{formatPercent(grupo.percentualFaturamento)} do faturamento analisado</p>
              </div>
              <span className="shrink-0 font-bold text-slate-900">{formatMoneyBRL(grupo.valor)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function PontoEquilibrio() {
  const [filtros, setFiltros] = useState({
    data_inicio: inicioMesAtual(),
    data_fim: fimMesAtual(),
    canal: "",
    fonte_margem: "media_12_meses_fechados",
    modo_custo_fiscal: "gerencial_completo",
  });
  const [impactoForm, setImpactoForm] = useState({
    descricao: "",
    valor: "",
    faturamento: "",
  });
  const [abaAtiva, setAbaAtiva] = useState("resumo");
  const [porteAnalise, setPorteAnalise] = useState("pequeno");
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");
  const [linhaDetalhe, setLinhaDetalhe] = useState(null);
  const [detalhesLinha, setDetalhesLinha] = useState(null);
  const [loadingDetalhes, setLoadingDetalhes] = useState(false);

  const percentualAtingido = Math.min(Number(dados?.percentual_atingido || 0), 100);
  const margemUsadaPercentual = Number(dados?.margem_usada_percentual ?? dados?.margem_contribuicao_percentual ?? 0);
  const margemPeriodoPercentual = Number(dados?.margem_periodo_percentual ?? dados?.margem_contribuicao_percentual ?? 0);
  const impactoValor = Number(impactoForm.valor || 0);
  const impactoSimulado = useMemo(() => {
    if (!dados) return null;
    return calcularImpactoPontoEquilibrio({
      despesasFixas: dados.despesas_fixas,
      pontoEquilibrio: dados.ponto_equilibrio,
      margemContribuicaoPercentual: dados.margem_usada_percentual ?? dados.margem_contribuicao_percentual,
      faturamento: dados.faturamento,
      faturamentoProjetado: impactoForm.faturamento,
      ticketMedio: dados.ticket_medio_usado ?? dados.ticket_medio,
      impactoCustoFixo: impactoValor,
    });
  }, [dados, impactoForm.faturamento, impactoValor]);
  const analiseCustos = useMemo(() => {
    if (!dados) return null;
    return montarAnaliseCustosPontoEquilibrio({
      dados,
      porte: porteAnalise,
      faturamentoProjetado: impactoForm.faturamento,
      impactoCustoFixo: impactoValor,
      impactoDescricao: impactoForm.descricao,
    });
  }, [dados, impactoForm.descricao, impactoForm.faturamento, impactoValor, porteAnalise]);

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
        text: `Faltam ${formatMoneyBRL(dados.falta_faturar || 0)} para cobrir os custos fixos pela margem usada.`,
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
      text: "Selecione um periodo com vendas para calcular a margem.",
    };
  }, [dados]);

  const montarParametrosPontoEquilibrio = (extras = {}) => {
    const params = {
      data_inicio: filtros.data_inicio,
      data_fim: filtros.data_fim,
      fonte_margem: filtros.fonte_margem,
      modo_custo_fiscal: filtros.modo_custo_fiscal,
      ...extras,
    };
    if (filtros.canal) {
      params.canais = filtros.canal;
    }
    return params;
  };

  const carregarDados = async () => {
    setLoading(true);
    setErro("");
    fecharDetalhesPontoEquilibrio();
    try {
      const response = await api.get("/financeiro/ponto-equilibrio", {
        params: montarParametrosPontoEquilibrio(),
        timeout: PONTO_EQUILIBRIO_REQUEST_TIMEOUT_MS,
      });
      setDados(response.data);
    } catch (error) {
      console.error("Erro ao carregar ponto de equilibrio:", error);
      setErro(error.response?.data?.detail || "Nao foi possivel carregar o ponto de equilibrio.");
    } finally {
      setLoading(false);
    }
  };

  function fecharDetalhesPontoEquilibrio() {
    setLinhaDetalhe(null);
    setDetalhesLinha(null);
    setLoadingDetalhes(false);
  }

  const abrirDetalhesPontoEquilibrio = async (linha, page = 1) => {
    if (!linha?.grupo) return;

    setLinhaDetalhe(linha);
    setLoadingDetalhes(true);
    setErro("");
    try {
      const response = await api.get("/financeiro/ponto-equilibrio/detalhes", {
        params: montarParametrosPontoEquilibrio({
          grupo: linha.grupo,
          page,
          page_size: 30,
        }),
        timeout: PONTO_EQUILIBRIO_REQUEST_TIMEOUT_MS,
      });
      setDetalhesLinha(response.data);
    } catch (error) {
      console.error("Erro ao carregar detalhes do ponto de equilibrio:", error);
      setErro(error.response?.data?.detail || "Nao foi possivel carregar os detalhes desta linha.");
    } finally {
      setLoadingDetalhes(false);
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
                  Quanto precisa vender para empatar os custos fixos pela margem de contribuicao escolhida.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-3 md:grid-cols-2 xl:grid-cols-[140px_140px_160px_210px_210px_auto]">
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
            <div>
              <label className="text-xs font-semibold text-slate-600">Fonte da margem</label>
              <select
                value={filtros.fonte_margem}
                onChange={(event) => setFiltros({ ...filtros, fonte_margem: event.target.value })}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                {MARGEM_PONTO_EQUILIBRIO_OPCOES.map((opcao) => (
                  <option key={opcao.value} value={opcao.value}>
                    {opcao.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Visao de custo</label>
              <select
                value={filtros.modo_custo_fiscal}
                onChange={(event) => setFiltros({ ...filtros, modo_custo_fiscal: event.target.value })}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                {MODO_CUSTO_FISCAL_OPCOES.map((opcao) => (
                  <option key={opcao.value} value={opcao.value}>
                    {opcao.label}
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
            pode vir do periodo atual ou de meses fechados. Ela usa o snapshot financeiro das
            vendas: receita, descontos, campanhas, taxas, entrega, comissoes, custo gerencial,
            CMV e outros custos variaveis sem duplicar contas geradas pela propria venda.
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

            <ModuleTabs
              active={abaAtiva}
              ariaLabel="Abas do ponto de equilibrio"
              onChange={setAbaAtiva}
              tabs={ABAS_PONTO_EQUILIBRIO}
            />

            {abaAtiva === "resumo" && (
              <>
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
                title="Margem usada"
                value={formatPercent(margemUsadaPercentual)}
                subtitle={`${dados.margem_usada_label || "Fonte atual"} | Periodo: ${formatPercent(margemPeriodoPercentual)}`}
                tone={margemUsadaPercentual > 0 ? "green" : "red"}
              />
              <MetricCard
                icon={ShoppingCart}
                title="Vendas necessarias"
                value={dados.vendas_necessarias == null ? "-" : String(dados.vendas_necessarias)}
                subtitle={`Ticket medio ${formatMoneyBRL(dados.ticket_medio_usado ?? dados.ticket_medio)}`}
                tone="slate"
              />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <h2 className="text-base font-semibold text-slate-900">Composicao da margem</h2>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">Receita produtos/servicos</span>
                    <span className="font-semibold text-emerald-700">{formatMoneyBRL(dados.receita_produtos_servicos ?? dados.faturamento)}</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">Receita entrega</span>
                    <span className="font-semibold text-emerald-700">{formatMoneyBRL(dados.receita_entrega || 0)}</span>
                  </div>
                  <div className="flex justify-between gap-4 border-t border-slate-100 pt-3">
                    <span className="text-slate-600">Faturamento total</span>
                    <span className="font-semibold text-slate-900">{formatMoneyBRL(dados.faturamento)}</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">CMV estimado</span>
                    <span className="font-semibold text-red-700">- {formatMoneyBRL(dados.cmv_estimado)}</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-slate-600">Custos de venda</span>
                    <span className="font-semibold text-red-700">- {formatMoneyBRL(dados.despesas_variaveis)}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 rounded-md bg-slate-50 p-3 text-xs text-slate-600">
                    <span>Descontos: {formatMoneyBRL(dados.descontos || 0)}</span>
                    <span>Campanhas: {formatMoneyBRL(dados.beneficios_campanhas || 0)}</span>
                    <span>Cartao: {formatMoneyBRL(dados.taxas_cartao || 0)}</span>
                    <span>Entrega: {formatMoneyBRL((dados.repasse_entrega || 0) + (dados.custo_operacional_entrega || 0))}</span>
                    <span>Comissoes: {formatMoneyBRL(dados.comissoes || 0)}</span>
                    <span>Custo gerencial: {formatMoneyBRL(dados.custo_fiscal || 0)}</span>
                    <span>Outros variaveis: {formatMoneyBRL(dados.outros_variaveis || 0)}</span>
                  </div>
                  <div className="border-t border-slate-100 pt-3">
                    <div className="flex justify-between gap-4">
                      <span className="font-semibold text-slate-700">Margem de contribuicao do periodo</span>
                      <span className="font-bold text-emerald-700">{formatMoneyBRL(dados.margem_contribuicao)}</span>
                    </div>
                    <div className="mt-2 flex justify-between gap-4 text-xs text-slate-500">
                      <span>Margem usada no calculo</span>
                      <span>{formatPercent(margemUsadaPercentual)} ({dados.margem_usada_label || "Fonte atual"})</span>
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

            <DetalhamentoMargemPanel
              dados={dados}
              onAbrirDetalhes={abrirDetalhesPontoEquilibrio}
            />
              </>
            )}

            {abaAtiva === "detalhamento" && (
              <DetalhamentoMargemPanel
                dados={dados}
                onAbrirDetalhes={abrirDetalhesPontoEquilibrio}
              />
            )}

            {abaAtiva === "simulador" && (
              <SimuladorImpactoPanel
                dados={dados}
                impactoForm={impactoForm}
                impactoSimulado={impactoSimulado}
                impactoValor={impactoValor}
                setImpactoForm={setImpactoForm}
              />
            )}

            {abaAtiva === "graficos" && analiseCustos && (
              <AnaliseCustosPanel
                analise={analiseCustos}
                porteAnalise={porteAnalise}
                setPorteAnalise={setPorteAnalise}
              />
            )}

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
      <DetalhesPontoEquilibrioDrawer
        linha={linhaDetalhe}
        detalhes={detalhesLinha}
        loading={loadingDetalhes}
        onClose={fecharDetalhesPontoEquilibrio}
        onPageChange={(page) => abrirDetalhesPontoEquilibrio(linhaDetalhe, page)}
      />
    </div>
  );
}
