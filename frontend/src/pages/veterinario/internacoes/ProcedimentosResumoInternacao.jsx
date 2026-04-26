import { Clock } from "lucide-react";
import { formatDateTime, formatQuantity } from "./internacaoUtils";

export default function ProcedimentosResumoInternacao({ procedimentos }) {
  return (
    <div className="mt-4">
      <p className="text-xs font-semibold text-gray-500 mb-2">Procedimentos desta internação</p>
      {procedimentos.length === 0 ? (
        <p className="text-xs text-gray-400">Nenhum procedimento registrado ainda.</p>
      ) : (
        <div className="space-y-2">
          {procedimentos.map((procedimento, index) => (
            <ProcedimentoResumoCard
              key={`${procedimento.id ?? index}_proc`}
              procedimento={procedimento}
              index={index}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ProcedimentoResumoCard({ procedimento, index }) {
  return (
    <div className="bg-white border border-emerald-100 rounded-lg px-3 py-2 text-xs">
      <div className="flex items-center gap-2 text-emerald-700 mb-1">
        <Clock size={10} />
        <span>
          {procedimento.horario_execucao
            ? formatDateTime(procedimento.horario_execucao)
            : formatDateTime(procedimento.data_hora)}
        </span>
      </div>
      <StatusProcedimento status={procedimento.status} />
      <p className="text-sm font-semibold text-emerald-800">{procedimento.medicamento || "Procedimento"}</p>
      <p className="text-gray-600">
        Dose: {procedimento.dose || "-"} - Via: {procedimento.via || "-"}
      </p>
      <QuantidadesProcedimento procedimento={procedimento} />
      <p className="text-gray-500">Responsável: {procedimento.executado_por || "-"}</p>
      <InsumosProcedimento procedimento={procedimento} index={index} />
      {procedimento.observacao_execucao && (
        <p className="text-gray-500 mt-1">Obs.: {procedimento.observacao_execucao}</p>
      )}
    </div>
  );
}

function StatusProcedimento({ status }) {
  return (
    <div className="mb-1">
      <span
        className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium ${
          status === "agendado"
            ? "bg-amber-100 text-amber-700 border border-amber-200"
            : "bg-emerald-100 text-emerald-700 border border-emerald-200"
        }`}
      >
        {status === "agendado" ? "Agendado" : "Concluído"}
      </span>
    </div>
  );
}

function QuantidadesProcedimento({ procedimento }) {
  if (
    procedimento.quantidade_prevista == null &&
    procedimento.quantidade_executada == null &&
    procedimento.quantidade_desperdicio == null
  ) {
    return null;
  }

  return (
    <p className="text-gray-600">
      Previsto: {formatQuantity(procedimento.quantidade_prevista, procedimento.unidade_quantidade)} - Feito:{" "}
      {formatQuantity(procedimento.quantidade_executada, procedimento.unidade_quantidade)} - Desperdício:{" "}
      {formatQuantity(procedimento.quantidade_desperdicio, procedimento.unidade_quantidade)}
    </p>
  );
}

function InsumosProcedimento({ procedimento, index }) {
  if (!Array.isArray(procedimento.insumos) || procedimento.insumos.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {procedimento.insumos.map((insumo, insumoIndex) => (
        <span
          key={`${procedimento.id ?? index}_insumo_${insumoIndex}`}
          className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700"
        >
          {insumo.nome || `Produto #${insumo.produto_id}`} - {formatQuantity(insumo.quantidade, insumo.unidade)}
        </span>
      ))}
    </div>
  );
}
