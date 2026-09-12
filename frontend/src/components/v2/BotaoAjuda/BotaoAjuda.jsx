import { HelpCircle } from "lucide-react";
import { forwardRef } from "react";

const BotaoAjuda = forwardRef(function BotaoAjuda({ onClick, texto = "Ajuda" }, ref) {
  return (
    <button
      ref={ref}
      type="button"
      onClick={onClick}
      aria-label={texto}
      title={texto}
      className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-300"
    >
      <HelpCircle className="h-[18px] w-[18px]" aria-hidden="true" />
    </button>
  );
});

export default BotaoAjuda;
