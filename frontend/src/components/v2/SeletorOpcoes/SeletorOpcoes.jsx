import { forwardRef } from "react";

// Grupo de opções únicas em formato de pill (filtro de período, alternância de visão etc.) —
// não é um campo de formulário (não usa InputRadio: aqui as opções têm largura pelo conteúdo,
// ficam numa barra de ferramentas e não têm label/erro/obrigatoriedade).
const SeletorOpcoes = forwardRef(function SeletorOpcoes(
  { aoSelecionar, opcoes, rotulo, valorSelecionado },
  ref,
) {
  return (
    <div ref={ref} className="flex flex-wrap items-center gap-2">
      {rotulo ? (
        <span className="mr-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
          {rotulo}
        </span>
      ) : null}
      <div
        role="group"
        aria-label={rotulo || undefined}
        className="flex flex-wrap items-center gap-2"
      >
        {opcoes.map((opcao) => {
          const selecionado = opcao.valor === valorSelecionado;
          return (
            <button
              key={opcao.valor}
              type="button"
              aria-pressed={selecionado}
              onClick={() => aoSelecionar?.(opcao.valor)}
              className={[
                "rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
                selecionado
                  ? "bg-slate-900 text-white dark:bg-cyan-500 dark:text-slate-950"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700",
              ].join(" ")}
            >
              {opcao.rotulo}
            </button>
          );
        })}
      </div>
    </div>
  );
});

export default SeletorOpcoes;
