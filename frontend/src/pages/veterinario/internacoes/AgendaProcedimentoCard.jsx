import { Check, Trash2 } from "lucide-react";
import ProcedimentoExecutadoResumo from "./ProcedimentoExecutadoResumo";
import { formatDateTime, formatQuantity } from "./internacaoUtils";

export default function AgendaProcedimentoCard({
  item,
  baiaExibicao,
  salvando,
  onReabrirProcedimento,
  onAbrirModalFeito,
  onRemoverProcedimentoAgenda,
}) {
  const ts = new Date(item.horario).getTime();
  const diffMin = Math.round((ts - Date.now()) / 60000);
  const alerta = obterClasseAlertaProcedimento(item, diffMin);

  return (
    <div className="border border-slate-200 rounded-xl p-3 bg-gradient-to-r from-white to-slate-50/40 shadow-sm flex flex-col md:flex-row md:items-center gap-3 md:gap-4">
      <div className="min-w-[160px] bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
        <p className="text-lg font-semibold text-slate-800 leading-none tabular-nums">
          {formatDateTime(item.horario)}
        </p>
        <span className={`inline-block mt-2 text-[11px] px-2 py-0.5 rounded-full font-medium ${alerta}`}>
          {item.feito ? "Concluido" : diffMin <= 0 ? "Atrasado" : `Em ${diffMin} min`}
        </span>
      </div>

      <div className="flex-1">
        <p className="text-base font-semibold text-indigo-800 leading-tight">{item.medicamento}</p>
        <p className="text-sm text-slate-600 mt-0.5">
          {item.pet_nome} - Baia {baiaExibicao}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 font-semibold">
            Dose: {item.dose || "-"}
          </span>
          {(item.quantidade_prevista || item.unidade_quantidade) && (
            <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 border border-blue-200">
              Previsto: {formatQuantity(item.quantidade_prevista, item.unidade_quantidade)}
            </span>
          )}
          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            Via: {item.via || "-"}
          </span>
          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            Lembrete: {item.lembrete_min || 30} min
          </span>
        </div>
        {item.observacoes && <p className="text-xs text-slate-500 mt-2 italic">{item.observacoes}</p>}
        {item.feito && <ProcedimentoExecutadoResumo item={item} />}
      </div>

      <div className="flex gap-2">
        {item.feito ? (
          <button
            type="button"
            onClick={onReabrirProcedimento}
            className="px-2.5 py-1.5 text-xs border border-emerald-200 bg-emerald-50 text-emerald-700 rounded-lg transition-colors flex items-center gap-1"
          >
            <Check size={12} />
            Concluido
          </button>
        ) : (
          <button
            type="button"
            onClick={() => onAbrirModalFeito(item)}
            disabled={salvando}
            className="px-2.5 py-1.5 text-xs border border-emerald-200 text-emerald-700 rounded-lg hover:bg-emerald-50 transition-colors flex items-center gap-1 disabled:opacity-60"
          >
            <Check size={12} />
            Feito
          </button>
        )}
        <button
          type="button"
          onClick={() => onRemoverProcedimentoAgenda(item.id)}
          disabled={salvando || item.feito}
          title={
            item.feito
              ? "Procedimento concluido nao pode ser excluido do historico clinico."
              : "Excluir procedimento agendado"
          }
          className="px-2.5 py-1.5 text-xs border border-rose-200 text-rose-700 rounded-lg hover:bg-rose-50 transition-colors flex items-center gap-1 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Trash2 size={12} />
          Excluir
        </button>
      </div>
    </div>
  );
}

function obterClasseAlertaProcedimento(item, diffMin) {
  if (item.feito) return "bg-emerald-100 text-emerald-700 border border-emerald-200";
  if (diffMin <= 0) return "bg-rose-100 text-rose-700 border border-rose-200";
  if (diffMin <= Number(item.lembrete_min || 30)) return "bg-amber-100 text-amber-700 border border-amber-200";
  return "bg-sky-100 text-sky-700 border border-sky-200";
}
