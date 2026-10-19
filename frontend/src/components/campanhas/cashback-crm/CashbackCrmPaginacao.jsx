import { ChevronLeft, ChevronRight } from "lucide-react";
import BotaoInteracao from "../../v2/BotaoInteracao/BotaoInteracao";

export default function CashbackCrmPaginacao({ pagina, paginacao, onChange, disabled = false }) {
  const paginas = Math.max(1, paginacao?.paginas || 1);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 dark:border-slate-700">
      <p className="text-xs text-slate-500 dark:text-slate-400">
        {paginacao?.total || 0} registro(s) · Página {pagina} de {paginas}
      </p>
      <div className="flex gap-2">
        <BotaoInteracao
          icon={ChevronLeft}
          tamanho="pequeno"
          disabled={disabled || pagina <= 1}
          onClick={() => onChange(pagina - 1)}
          aria-label="Página anterior"
        >
          Anterior
        </BotaoInteracao>
        <BotaoInteracao
          icon={ChevronRight}
          tamanho="pequeno"
          disabled={disabled || pagina >= paginas}
          onClick={() => onChange(pagina + 1)}
          aria-label="Próxima página"
        >
          Próxima
        </BotaoInteracao>
      </div>
    </div>
  );
}
