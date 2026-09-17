import { Boxes, DollarSign, Receipt } from "lucide-react";

import { formatMoneyBRL } from "../../utils/formatters";

const quantidade = (valor) =>
  Number(valor || 0).toLocaleString("pt-BR", {
    maximumFractionDigits: 3,
  });

const quantidadeComRotulo = (valor, singular, plural) =>
  `${quantidade(valor)} ${Number(valor || 0) === 1 ? singular : plural}`;

const CONFIGURACAO = {
  total_gasto: {
    titulo: "Cliente que mais gastou",
    Icone: DollarSign,
    cor: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200",
    valor: (cliente) => formatMoneyBRL(cliente.total_gasto),
    detalhe: (cliente) =>
      `${quantidadeComRotulo(cliente.total_compras, "compra", "compras")} no período`,
  },
  total_compras: {
    titulo: "Cliente que mais comprou",
    Icone: Receipt,
    cor: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-200",
    valor: (cliente) => quantidadeComRotulo(cliente.total_compras, "compra", "compras"),
    detalhe: (cliente) => formatMoneyBRL(cliente.total_gasto),
  },
  total_itens: {
    titulo: "Maior quantidade de itens",
    Icone: Boxes,
    cor: "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-500/30 dark:bg-violet-500/10 dark:text-violet-200",
    valor: (cliente) => quantidadeComRotulo(cliente.total_itens, "item", "itens"),
    detalhe: (cliente) =>
      `${quantidadeComRotulo(cliente.total_compras, "compra", "compras")} no período`,
  },
};

export default function RankingClientesDestaques({ lideres, onSelecionarMetrica }) {
  return (
    <section aria-labelledby="ranking-destaques-title">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2
            id="ranking-destaques-title"
            className="font-semibold text-slate-900 dark:text-slate-100"
          >
            Destaques do período
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Os três líderes são calculados somente com vendas finalizadas e identificadas.
          </p>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {Object.entries(CONFIGURACAO).map(([metrica, config]) => {
          const cliente = lideres?.[metrica];
          const Icone = config.Icone;
          return (
            <button
              key={metrica}
              type="button"
              onClick={() => onSelecionarMetrica(metrica)}
              className={`rounded-xl border p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${config.cor}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-wide opacity-80">
                    {config.titulo}
                  </p>
                  <p className="mt-3 truncate text-lg font-bold text-slate-950 dark:text-slate-100">
                    {cliente?.nome || "Sem vendas no período"}
                  </p>
                  {cliente ? (
                    <>
                      <p className="mt-1 text-2xl font-extrabold text-slate-950 dark:text-white">
                        {config.valor(cliente)}
                      </p>
                      <p className="mt-1 text-xs opacity-80">{config.detalhe(cliente)}</p>
                    </>
                  ) : null}
                </div>
                <span className="rounded-xl bg-white/70 p-3 shadow-sm dark:bg-slate-950/30">
                  <Icone className="h-6 w-6" aria-hidden="true" />
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
