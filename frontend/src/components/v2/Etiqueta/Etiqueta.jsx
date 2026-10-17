import { TONS_BADGE } from "../utils/tons";

// Etiqueta pequena de status ou categoria dentro de uma linha/cartão (prazo, tipo, dose, contagem).
// "tom" usa o mesmo vocabulário de BotaoBase.variante (neutro/sucesso/perigo/informativo/atencao).
// Sempre carrega texto (children) — a cor nunca é o único sinal; o ícone é opcional e decorativo.
export default function Etiqueta({ children, icone: Icone, tom = "neutro" }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold",
        TONS_BADGE[tom] || TONS_BADGE.neutro,
      ].join(" ")}
    >
      {Icone ? <Icone className="h-3 w-3" aria-hidden="true" /> : null}
      {children}
    </span>
  );
}
