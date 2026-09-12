import {
  STYLEGUIDE_STATUS,
  contarPorStatus,
  styleGuideCatalog,
  totalDeItens,
} from "../styleGuideCatalog";

const CARTAO_INTENT_CLASSES = {
  slate: "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900",
  emerald: "border-emerald-200 bg-emerald-50 dark:border-emerald-400/30 dark:bg-emerald-500/10",
  amber: "border-amber-200 bg-amber-50 dark:border-amber-400/30 dark:bg-amber-500/10",
};

const BADGE_INTENT_CLASSES = {
  success:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-400/30 dark:bg-emerald-500/10 dark:text-emerald-200",
  warning:
    "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-200",
  neutral:
    "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300",
};

function Cartao({ intent, label, subtitle, value }) {
  return (
    <div
      className={[
        "flex flex-col justify-between rounded-lg border p-4",
        CARTAO_INTENT_CLASSES[intent],
      ].join(" ")}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </div>
      <div className="mt-2 text-2xl font-bold leading-tight text-slate-950 dark:text-slate-100">
        {value}
      </div>
      <p className="mt-1 text-xs leading-snug text-slate-500 dark:text-slate-400">{subtitle}</p>
    </div>
  );
}

function Selo({ intent, children }) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium leading-none",
        BADGE_INTENT_CLASSES[intent],
      ].join(" ")}
    >
      {children}
    </span>
  );
}

export default function StyleGuideProgress() {
  const contagem = contarPorStatus();
  const total = totalDeItens();
  const percentualConsolidado = total ? Math.round((contagem.pronto / total) * 100) : 0;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Cartao
          label="Total no catálogo v2"
          value={total}
          subtitle="componentes mapeados"
          intent="slate"
        />
        <Cartao
          label={STYLEGUIDE_STATUS.pronto.label}
          value={contagem.pronto}
          subtitle="já existem em components/v2/"
          intent="emerald"
        />
        <Cartao
          label={STYLEGUIDE_STATUS.planejado.label}
          value={contagem.planejado}
          subtitle="ainda não foram criados"
          intent="amber"
        />
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
          <span>Pronto em components/v2/</span>
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
        <table className="w-full min-w-[560px] text-left text-sm">
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
                    <Selo intent={STYLEGUIDE_STATUS[item.status].intent}>
                      {STYLEGUIDE_STATUS[item.status].label}
                    </Selo>
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
