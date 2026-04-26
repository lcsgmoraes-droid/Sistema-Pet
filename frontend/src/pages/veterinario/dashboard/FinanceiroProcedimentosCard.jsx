import { formatMoneyBRL, formatPercent } from "../../../utils/formatters";

export default function FinanceiroProcedimentosCard({ dados }) {
  const modeloParceiro = dados?.modelo_operacional_financeiro === "parceiro";

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 lg:col-span-3">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-700">Financeiro de procedimentos (30d)</h3>
          <p className="text-xs text-gray-400">Baseado nos insumos realmente vinculados em cada procedimento.</p>
        </div>
        <span className="text-xs font-semibold rounded-full px-2 py-1 bg-emerald-50 text-emerald-700">
          Margem {formatPercent(dados?.margem_percentual_procedimentos_30d ?? 0)}
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <ResumoFinanceiroCard titulo="Faturamento" valor={dados?.faturamento_procedimentos_30d ?? 0} cor="text-blue-700" />
        <ResumoFinanceiroCard titulo="Custo" valor={dados?.custo_procedimentos_30d ?? 0} cor="text-amber-700" />
        <ResumoFinanceiroCard
          titulo="Margem"
          valor={dados?.margem_procedimentos_30d ?? 0}
          cor={(dados?.margem_procedimentos_30d ?? 0) < 0 ? "text-red-600" : "text-emerald-700"}
        />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
        <ResumoFinanceiroCard
          titulo={modeloParceiro ? "Repasse empresa" : "Entrada empresa"}
          valor={
            modeloParceiro
              ? dados?.repasse_empresa_procedimentos_30d ?? 0
              : dados?.entrada_empresa_procedimentos_30d ?? 0
          }
          cor="text-sky-700"
        />
        <ResumoFinanceiroCard
          titulo={modeloParceiro ? "Líquido veterinário" : "Comissão empresa"}
          valor={
            modeloParceiro
              ? dados?.receita_tenant_procedimentos_30d ?? 0
              : dados?.comissao_empresa_pct_padrao ?? 0
          }
          cor="text-violet-700"
          percentual={!modeloParceiro}
        />
      </div>
    </div>
  );
}

function ResumoFinanceiroCard({ titulo, valor, cor, percentual = false }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-gray-400">{titulo}</p>
      <p className={`text-2xl font-bold mt-1 ${cor}`}>
        {percentual ? formatPercent(valor) : formatMoneyBRL(valor)}
      </p>
    </div>
  );
}
