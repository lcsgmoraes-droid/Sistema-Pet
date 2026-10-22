import { useDroppable } from "@dnd-kit/core";
import CrmCard, { chaveDoCard } from "./CrmCard";
import { ROTULO_TIPO_DE_COLUNA, formatarValor } from "./crmUtils";

export default function CrmColuna({ coluna, mostrarLoja, movendoId, onAbrir }) {
  const { isOver, setNodeRef } = useDroppable({ id: coluna.chave, data: { coluna } });
  const ocultos = coluna.total - coluna.cards.length;

  return (
    <section
      aria-label={`Coluna ${coluna.nome}`}
      className="flex w-72 flex-none flex-col rounded-2xl bg-slate-100 dark:bg-slate-950/60"
    >
      <header className="px-3 pt-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">{coluna.nome}</h2>
          <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200">
            {coluna.total}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          {ROTULO_TIPO_DE_COLUNA[coluna.tipo]}
          {coluna.valor_total > 0 ? ` · ${formatarValor(coluna.valor_total)}` : ""}
          {coluna.janela_dias ? ` · últimos ${coluna.janela_dias} dias` : ""}
        </p>
      </header>

      <ul
        ref={setNodeRef}
        className={[
          "m-2 flex min-h-[120px] flex-1 flex-col gap-2 rounded-xl p-1 transition-colors",
          isOver ? "bg-blue-100 ring-2 ring-blue-400 dark:bg-blue-950/50" : "",
        ].join(" ")}
      >
        {coluna.cards.length === 0 ? (
          <li className="list-none px-2 py-6 text-center text-xs text-slate-500 dark:text-slate-400">
            Nenhum card aqui. Arraste um card para esta coluna.
          </li>
        ) : null}
        {coluna.cards.map((card) => (
          <CrmCard
            key={chaveDoCard(card)}
            card={card}
            mostrarLoja={mostrarLoja}
            movendo={movendoId === chaveDoCard(card)}
            onAbrir={onAbrir}
          />
        ))}
        {ocultos > 0 ? (
          <li className="list-none px-2 py-1 text-center text-xs text-slate-500 dark:text-slate-400">
            Mostrando {coluna.cards.length} de {coluna.total}. Use a busca para achar os outros.
          </li>
        ) : null}
      </ul>
    </section>
  );
}
