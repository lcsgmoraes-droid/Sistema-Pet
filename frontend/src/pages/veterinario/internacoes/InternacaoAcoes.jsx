import { Activity, ArrowUpCircle } from "lucide-react";

export default function InternacaoAcoes({
  internacao,
  onAbrirAlta,
  onAbrirEvolucao,
  onAbrirFichaPet,
  onAbrirHistoricoPet,
  onAbrirInsumoRapido,
}) {
  return (
    <div className="flex gap-2" onClick={(event) => event.stopPropagation()}>
      <button
        type="button"
        onClick={() => onAbrirInsumoRapido(internacao.id)}
        className="flex items-center gap-1 text-xs px-2 py-1 border border-emerald-200 text-emerald-700 rounded-lg hover:bg-emerald-50"
      >
        + Insumo
      </button>
      <button
        type="button"
        onClick={() => onAbrirEvolucao(internacao.id)}
        className="flex items-center gap-1 text-xs px-2 py-1 border border-blue-200 text-blue-600 rounded-lg hover:bg-blue-50"
      >
        <Activity size={12} />
        Evolução
      </button>
      <button
        type="button"
        onClick={() => onAbrirAlta(internacao.id)}
        className="flex items-center gap-1 text-xs px-2 py-1 border border-green-200 text-green-600 rounded-lg hover:bg-green-50"
      >
        <ArrowUpCircle size={12} />
        Alta
      </button>
      <button
        type="button"
        onClick={() => onAbrirFichaPet(internacao.pet_id)}
        className="flex items-center gap-1 text-xs px-2 py-1 border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50"
      >
        Ficha do pet
      </button>
      <button
        type="button"
        onClick={() => onAbrirHistoricoPet(internacao.pet_id, internacao.pet_nome ?? `Pet #${internacao.pet_id}`)}
        className="flex items-center gap-1 text-xs px-2 py-1 border border-indigo-200 text-indigo-600 rounded-lg hover:bg-indigo-50"
      >
        Detalhes
      </button>
    </div>
  );
}
