import { STATUS_CORES, formatDateTime, formatQuantity } from "./internacaoUtils";

export default function HistoricoInternacoesPetModal({
  historicoPetInfo,
  historicoPet,
  carregando,
  onClose,
}) {
  if (!historicoPetInfo) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl p-6 max-h-[85vh] overflow-auto">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="font-bold text-gray-800">Histórico de internações</h2>
            <p className="text-sm text-gray-500">{historicoPetInfo.petNome}</p>
          </div>
          <button onClick={onClose} className="px-2 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">
            Fechar
          </button>
        </div>

        {carregando ? (
          <p className="text-sm text-gray-500">Carregando histórico...</p>
        ) : historicoPet.length === 0 ? (
          <p className="text-sm text-gray-500">Nenhuma internação encontrada para este pet.</p>
        ) : (
          <div className="space-y-3">
            {historicoPet.map((hist) => (
              <div key={hist.internacao_id} className="border border-gray-200 rounded-xl p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-gray-800">
                    Internação #{hist.internacao_id} • {hist.box ? `Baia ${hist.box}` : "Sem baia"}
                  </p>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CORES[hist.status] ?? "bg-gray-100 text-gray-700"}`}>
                    {hist.status}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Entrada: {formatDateTime(hist.data_entrada)}
                  {hist.data_saida ? ` • Alta: ${formatDateTime(hist.data_saida)}` : ""}
                </p>
                <p className="text-xs text-gray-600 mt-1">Motivo: {hist.motivo || "—"}</p>
                <p className="text-xs text-gray-600 mt-1">
                  Evoluções: {hist.evolucoes?.length ?? 0} • Procedimentos: {hist.procedimentos?.length ?? 0}
                </p>
                {Array.isArray(hist.procedimentos) && hist.procedimentos.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {hist.procedimentos.map((proc, idx) => (
                      <div key={`${hist.internacao_id}_proc_${proc.id ?? idx}`} className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-xs">
                        <p className="font-semibold text-gray-800">{proc.medicamento || "Procedimento"}</p>
                        <p className="text-gray-500">
                          {proc.horario_execucao ? formatDateTime(proc.horario_execucao) : formatDateTime(proc.data_hora)}
                        </p>
                        {(proc.quantidade_prevista != null || proc.quantidade_executada != null || proc.quantidade_desperdicio != null) && (
                          <p className="mt-1 text-gray-600">
                            Previsto: {formatQuantity(proc.quantidade_prevista, proc.unidade_quantidade)} • Feito: {formatQuantity(proc.quantidade_executada, proc.unidade_quantidade)} • Desperdício: {formatQuantity(proc.quantidade_desperdicio, proc.unidade_quantidade)}
                          </p>
                        )}
                        {Array.isArray(proc.insumos) && proc.insumos.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {proc.insumos.map((insumo, insumoIdx) => (
                              <span key={`${hist.internacao_id}_proc_${idx}_insumo_${insumoIdx}`} className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                                {insumo.nome || `Produto #${insumo.produto_id}`} • {formatQuantity(insumo.quantidade, insumo.unidade)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
