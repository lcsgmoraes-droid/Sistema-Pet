import { BarChart3 } from "lucide-react";
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
import { FAIXAS_PORTE_PETSHOP } from "../pontoEquilibrioImpactoUtils";
import { formatMoneyBRL, formatPercent } from "../../utils/formatters";
import { CORES_GRAFICO_CUSTOS, TOOLTIP_FAIXAS_PORTE } from "./pontoEquilibrioConstants";
import { TooltipMoeda, TooltipPercentual } from "./PontoEquilibrioTooltips";
import {
  formatarImpactoMoeda,
  formatarVariacaoPercentual,
  statusParecerClasses,
  statusParecerLabelGerencial,
} from "./pontoEquilibrioUtils";

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
          <p
            className={
              parecer.diferencaValor > 0 ? "text-xs text-red-700" : "text-xs text-emerald-700"
            }
          >
            {formatarVariacaoPercentual(parecer.diferencaPercentual)} (
            {formatarImpactoMoeda(parecer.diferencaValor)})
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

export default function AnaliseCustosPanel({ analise, porteAnalise, setPorteAnalise }) {
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
                Parecer gerencial com metas setoriais ajustadas para caber no limite saudavel de
                custo fixo total. As referencias setoriais aparecem como contexto de comparacao.
              </p>
            </div>
          </div>

          <div className="w-full rounded-lg border border-slate-200 bg-slate-50 p-3 lg:w-72">
            <div className="flex items-center justify-between gap-2">
              <label className="text-xs font-semibold uppercase text-slate-600">
                Porte do petshop
              </label>
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
            <p className="mt-2 text-xs text-slate-600">{analise.porte.faixaMensal}</p>
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
                    <Cell
                      key={entry.id}
                      fill={CORES_GRAFICO_CUSTOS[index % CORES_GRAFICO_CUSTOS.length]}
                    />
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
                <XAxis
                  dataKey="nome"
                  tick={{ fontSize: 11 }}
                  interval={0}
                  angle={-12}
                  textAnchor="end"
                  height={70}
                />
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
                <p className="text-xs text-slate-500">
                  {formatPercent(grupo.percentualFaturamento)} do faturamento analisado
                </p>
              </div>
              <span className="shrink-0 font-bold text-slate-900">
                {formatMoneyBRL(grupo.valor)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
