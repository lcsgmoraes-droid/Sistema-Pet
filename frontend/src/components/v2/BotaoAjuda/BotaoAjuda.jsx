import { HelpCircle } from "lucide-react";
import { forwardRef } from "react";

const TAMANHOS = {
  pequeno: { botao: "h-8 w-8", icone: "h-4 w-4" },
  normal: { botao: "h-9 w-9", icone: "h-5 w-5" },
  grande: { botao: "h-11 w-11", icone: "h-6 w-6" },
};

const BotaoAjuda = forwardRef(function BotaoAjuda(
  { onClick, tamanho = "normal", texto = "Ajuda", ...rest },
  ref,
) {
  const medida = TAMANHOS[tamanho] || TAMANHOS.normal;

  return (
    <button
      {...rest}
      ref={ref}
      type="button"
      onClick={onClick}
      aria-label={texto}
      title={texto}
      className={[
        "inline-flex shrink-0 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-300",
        medida.botao,
      ].join(" ")}
    >
      <HelpCircle className={medida.icone} aria-hidden="true" />
    </button>
  );
});

export default BotaoAjuda;
