import { useDraggable } from "@dnd-kit/core";
import { AlertTriangle, CalendarClock, Clock, GripVertical, Store, UserRoundX } from "lucide-react";
import {
  formatarValor,
  precisaDeAtencaoPorTempo,
  rotuloDaOportunidade,
  situacaoDoPasso,
} from "./crmUtils";

// Atenção usa amarelo/laranja/vermelho; informativo usa azul/verde/rosa/roxo. Sempre com texto.
const ESTILO_DO_PASSO = {
  sem_passo: "text-amber-700 dark:text-amber-300",
  hoje: "text-amber-700 dark:text-amber-300",
  atrasado: "font-semibold text-red-700 dark:text-red-300",
  futuro: "text-slate-600 dark:text-slate-300",
};

export function chaveDoCard(card) {
  return `${card.loja_id}:${card.id}`;
}

export default function CrmCard({ card, mostrarLoja, movendo, onAbrir }) {
  const { attributes, isDragging, listeners, setActivatorNodeRef, setNodeRef, transform } =
    useDraggable({
      id: chaveDoCard(card),
      data: { card },
    });
  const passo = situacaoDoPasso(card.proximo_passo);
  const IconeDoPasso = passo.codigo === "atrasado" ? AlertTriangle : CalendarClock;
  const estilo = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`, zIndex: 20 }
    : undefined;

  return (
    <li
      ref={setNodeRef}
      style={estilo}
      onDoubleClick={() => onAbrir?.(card)}
      className={[
        "list-none rounded-xl border border-slate-200 bg-white p-3 text-sm shadow-sm",
        "dark:border-slate-700 dark:bg-slate-900",
        isDragging ? "opacity-80 shadow-lg" : "",
        movendo ? "pointer-events-none opacity-50" : "",
      ].join(" ")}
    >
      {mostrarLoja ? (
        <p className="mb-1 flex items-center gap-1 text-xs font-medium text-violet-700 dark:text-violet-300">
          <Store className="h-3.5 w-3.5" aria-hidden="true" />
          {card.loja_nome}
        </p>
      ) : null}

      <div className="flex items-start justify-between gap-2">
        {/* Só a alça arrasta (mouse, toque e teclado): o resto do card rola e clica normalmente. */}
        <button
          type="button"
          ref={setActivatorNodeRef}
          {...attributes}
          {...listeners}
          aria-label={`Mover o card de ${card.nome}. Espaço pega, setas movem, espaço solta.`}
          className="-ml-1 flex h-11 w-8 flex-none cursor-grab touch-none items-center justify-center rounded-md text-slate-400 hover:text-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:text-slate-200"
        >
          <GripVertical className="h-5 w-5" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={() => onAbrir?.(card)}
          className="min-h-[44px] flex-1 text-left font-semibold text-slate-900 hover:underline dark:text-slate-100 sm:min-h-0"
        >
          {card.nome}
        </button>
        {card.ciclo > 1 ? (
          <span className="rounded-md bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/40 dark:text-blue-200">
            Ciclo {card.ciclo}
          </span>
        ) : null}
      </div>

      {card.sem_cadastro ? (
        <p className="mt-1 flex items-center gap-1 text-xs text-blue-700 dark:text-blue-300">
          <UserRoundX className="h-3.5 w-3.5" aria-hidden="true" />
          Lead novo · sem cadastro
        </p>
      ) : null}

      {card.pets?.length ? (
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Pets: {card.pets.join(", ")}
        </p>
      ) : null}

      {card.oportunidades?.length ? (
        <ul className="mt-2 flex flex-wrap gap-1">
          {card.oportunidades.map((oportunidade) => (
            <li
              key={oportunidade.id}
              className={[
                "rounded-md px-1.5 py-0.5 text-xs",
                oportunidade.generica
                  ? "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                  : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200",
              ].join(" ")}
            >
              {rotuloDaOportunidade(oportunidade)}
            </li>
          ))}
        </ul>
      ) : null}

      <p
        className={["mt-2 flex items-center gap-1 text-xs", ESTILO_DO_PASSO[passo.codigo]].join(
          " ",
        )}
      >
        <IconeDoPasso className="h-3.5 w-3.5" aria-hidden="true" />
        {passo.texto}
      </p>

      <div className="mt-1 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        {card.dias_na_coluna != null ? (
          <span
            className={[
              "flex items-center gap-1",
              precisaDeAtencaoPorTempo(card) ? "text-amber-700 dark:text-amber-300" : "",
            ].join(" ")}
          >
            <Clock className="h-3.5 w-3.5" aria-hidden="true" />
            {card.dias_na_coluna === 0
              ? "Hoje na coluna"
              : `${card.dias_na_coluna} dia(s) na coluna`}
          </span>
        ) : (
          <span />
        )}
        {card.valor_estimado != null ? <span>{formatarValor(card.valor_estimado)}</span> : null}
      </div>
    </li>
  );
}
