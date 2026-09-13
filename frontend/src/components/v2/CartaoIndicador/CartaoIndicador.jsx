import { ArrowRight } from "lucide-react";
import { forwardRef } from "react";
import { TONS_ICONE } from "../utils/tons";

// Substitui MetricCard/CompactMetricCard/PriorityCard do dashboard financeiro — um único formato
// de cartão indicador. O ícone à esquerda muda de cor conforme "tom" (mesmo vocabulário do
// BotaoBase.variante); a seta à direita só aparece quando o cartão navega para outro lugar
// (aoClicar) e é sempre o mesmo ícone, independente do tom — antes cada cartão usava um ícone
// diferente aqui (seta ou check) para dizer a mesma coisa.
const CartaoIndicador = forwardRef(function CartaoIndicador(
  { aoClicar, children, detalhe, icone: Icone, titulo, tom = "neutro" },
  ref,
) {
  const Wrapper = aoClicar ? "button" : "div";

  return (
    <Wrapper
      ref={ref}
      type={aoClicar ? "button" : undefined}
      onClick={aoClicar}
      aria-label={aoClicar ? titulo : undefined}
      className={[
        "flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm dark:border-slate-800 dark:bg-slate-900",
        aoClicar
          ? "group transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md dark:hover:border-slate-700"
          : "",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <span className={`rounded-xl p-2 ${TONS_ICONE[tom] || TONS_ICONE.neutro}`}>
          <Icone className="h-4 w-4" aria-hidden="true" />
        </span>
        {aoClicar ? (
          <ArrowRight
            className="h-4 w-4 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-slate-500 dark:text-slate-600"
            aria-hidden="true"
          />
        ) : null}
      </div>
      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {titulo}
      </p>
      <div className="mt-1">{children}</div>
      {detalhe ? (
        <p className="mt-auto pt-2 text-xs leading-snug text-slate-500 dark:text-slate-400">
          {detalhe}
        </p>
      ) : null}
    </Wrapper>
  );
});

export default CartaoIndicador;
