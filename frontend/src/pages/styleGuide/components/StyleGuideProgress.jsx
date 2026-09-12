import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import StatusBadge from "../../../components/ui/StatusBadge";
import {
  STYLEGUIDE_STATUS,
  contarPorStatus,
  styleGuideCatalog,
  totalDeItens,
} from "../styleGuideCatalog";

export default function StyleGuideProgress() {
  const contagem = contarPorStatus();
  const total = totalDeItens();
  const percentualConsolidado = total
    ? Math.round(((contagem.pronto + contagem.legado) / total) * 100)
    : 0;

  return (
    <div className="space-y-5">
      <MetricGrid>
        <MetricCard
          label="Total no catálogo"
          value={total}
          subtitle="componentes mapeados no roadmap"
          intent="slate"
        />
        <MetricCard
          label={STYLEGUIDE_STATUS.pronto.label}
          value={contagem.pronto}
          subtitle="já seguem o padrão novo"
          intent="emerald"
        />
        <MetricCard
          label={STYLEGUIDE_STATUS.legado.label}
          value={contagem.legado}
          subtitle="funcionam, mas fora do padrão"
          intent="amber"
        />
        <MetricCard
          label={STYLEGUIDE_STATUS.planejado.label}
          value={contagem.planejado}
          subtitle="ainda não foram criados"
          intent="slate"
        />
      </MetricGrid>

      <div>
        <div className="mb-1 flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
          <span>Existe algo utilizável hoje (pronto + legado)</span>
          <span>{percentualConsolidado}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
          <div
            className="h-full rounded-full bg-blue-600 transition-all"
            style={{ width: `${percentualConsolidado}%` }}
          />
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
            <tr>
              <th className="px-4 py-2">Categoria</th>
              <th className="px-4 py-2">Componente</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Onde</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {styleGuideCatalog.map((grupo) =>
              grupo.itens.map((item, index) => (
                <tr key={`${grupo.categoria}-${item.nome}`}>
                  {index === 0 ? (
                    <td
                      rowSpan={grupo.itens.length}
                      className="align-top px-4 py-2 font-semibold text-slate-700 dark:text-slate-200"
                    >
                      {grupo.categoria}
                      <div className="mt-0.5 text-xs font-normal text-slate-400">
                        {grupo.origem}
                      </div>
                    </td>
                  ) : null}
                  <td className="px-4 py-2 text-slate-900 dark:text-slate-100">
                    {item.nome}
                    {item.descricao ? (
                      <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                        {item.descricao}
                      </div>
                    ) : null}
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge intent={STYLEGUIDE_STATUS[item.status].intent}>
                      {STYLEGUIDE_STATUS[item.status].label}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-slate-500 dark:text-slate-400">
                    {item.arquivo || "—"}
                  </td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
