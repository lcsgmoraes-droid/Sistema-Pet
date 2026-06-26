import { formatMoneyBRL } from "../../utils/formatters";
import { CENARIOS_RAPIDOS, DEFAULT_IMPACTO_FORM } from "./pontoEquilibrioConstants";
import { formatarImpactoMoeda, formatarImpactoVendas } from "./pontoEquilibrioUtils";

export default function SimuladorImpactoPanel({
  dados,
  impactoForm,
  impactoSimulado,
  impactoValor,
  setImpactoForm,
}) {
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
            onChange={(event) =>
              setImpactoForm({ ...impactoForm, faturamento: event.target.value })
            }
            placeholder={formatMoneyBRL(dados.faturamento)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600">
            Impacto mensal no custo fixo
          </label>
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
          onClick={() => setImpactoForm(DEFAULT_IMPACTO_FORM)}
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
            <p
              className={
                impactoValor >= 0 ? "mt-1 text-xs text-red-700" : "mt-1 text-xs text-emerald-700"
              }
            >
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
            <p className="text-xs font-semibold uppercase text-slate-500">
              Resultado projetado do mes
            </p>
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
