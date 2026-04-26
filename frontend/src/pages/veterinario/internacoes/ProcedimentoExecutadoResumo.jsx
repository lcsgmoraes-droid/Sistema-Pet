import { formatDateTime, formatQuantity } from "./internacaoUtils";

export default function ProcedimentoExecutadoResumo({ item }) {
  return (
    <div className="mt-2 bg-emerald-50 border border-emerald-200 rounded-md px-2 py-1.5">
      <p className="text-[11px] text-emerald-700 font-semibold">
        Feito por: {item.feito_por || "-"} - {item.horario_execucao ? formatDateTime(item.horario_execucao) : "-"}
      </p>
      {(item.quantidade_executada || item.quantidade_desperdicio) && (
        <p className="text-[11px] text-emerald-800">
          Feito: {formatQuantity(item.quantidade_executada, item.unidade_quantidade)} - Desperdicio:{" "}
          {formatQuantity(item.quantidade_desperdicio, item.unidade_quantidade)}
        </p>
      )}
      {item.observacao_execucao && (
        <p className="text-[11px] text-emerald-800">Obs. execucao: {item.observacao_execucao}</p>
      )}
    </div>
  );
}
