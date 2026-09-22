import { forwardRef } from "react";
import { AlertCircle } from "lucide-react";

// Abas horizontais com ícone — estilo GitHub (ícone + rótulo lado a lado). A aba ativa
// usa o mesmo degradê do menu principal (SidebarMenu) para reforçar a identidade visual
// do sistema. `descricao` vira dica nativa ao passar o mouse, em vez de disputar espaço
// com o rótulo. `invalida` mostra um ícone de alerta ao lado do rótulo (nunca só cor) —
// sinaliza que aquela aba tem campo obrigatório pendente, sem precisar abrir a aba pra
// descobrir.
const AbasNavegacao = forwardRef(function AbasNavegacao(
  { abas = [], ariaLabel = "Abas", ativa, className = "", onChange },
  ref,
) {
  return (
    <div
      ref={ref}
      role="tablist"
      aria-label={ariaLabel}
      className={[
        "flex gap-1 overflow-x-auto border-b border-slate-200 pb-1 dark:border-slate-700",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {abas.map((aba) => {
        const Icone = aba.icon;
        const selecionada = aba.id === ativa;

        return (
          <button
            key={aba.id}
            type="button"
            role="tab"
            aria-selected={selecionada}
            title={aba.descricao}
            onClick={() => onChange?.(aba.id)}
            className={[
              "flex flex-none items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
              selecionada
                ? "bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 shadow-sm dark:from-cyan-500/15 dark:to-blue-500/15 dark:text-cyan-200"
                : "text-slate-500 hover:bg-white/60 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200",
            ].join(" ")}
          >
            {Icone ? <Icone className="h-4 w-4" aria-hidden="true" /> : null}
            {aba.label}
            {aba.invalida ? (
              <AlertCircle
                className="h-3.5 w-3.5 flex-none text-amber-600 dark:text-amber-400"
                aria-label="Pendência nesta aba"
              />
            ) : null}
          </button>
        );
      })}
    </div>
  );
});

export default AbasNavegacao;
