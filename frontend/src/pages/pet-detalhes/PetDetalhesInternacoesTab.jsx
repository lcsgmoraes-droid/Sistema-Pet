import { formatarDataHora } from "./petDetalhesUtils";

function InternacaoSubList({ empty, items, renderItem, title }) {
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
      <p className="text-xs font-semibold text-gray-600 mb-2">
        {title} ({items?.length || 0})
      </p>
      {(items?.length || 0) === 0 ? (
        <p className="text-xs text-gray-400">{empty}</p>
      ) : (
        <div className="space-y-2">{items.map(renderItem)}</div>
      )}
    </div>
  );
}

export default function PetDetalhesInternacoesTab({
  historicoInternacoes,
  loadingInternacoes,
  onOpenInternacoes,
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900">HistÃ³rico de InternaÃ§Ãµes</h2>
        <button
          onClick={onOpenInternacoes}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
        >
          Abrir mÃ³dulo de internaÃ§Ãµes
        </button>
      </div>

      {loadingInternacoes ? (
        <div className="text-center py-10 text-gray-500">Carregando histÃ³rico...</div>
      ) : historicoInternacoes.length === 0 ? (
        <div className="text-center py-12 text-gray-500 border border-gray-200 rounded-lg bg-gray-50">
          Nenhuma internaÃ§Ã£o registrada para este pet.
        </div>
      ) : (
        <div className="space-y-4">
          {historicoInternacoes.map((internacao) => (
            <div
              key={internacao.internacao_id}
              className="border border-gray-200 rounded-lg p-4 bg-white"
            >
              <div className="flex items-center justify-between gap-3 mb-2">
                <p className="font-semibold text-gray-800">
                  InternaÃ§Ã£o #{internacao.internacao_id}{" "}
                  {internacao.box ? `â€¢ Baia ${internacao.box}` : "â€¢ Sem baia"}
                </p>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    internacao.status === "alta"
                      ? "bg-green-100 text-green-700"
                      : "bg-blue-100 text-blue-700"
                  }`}
                >
                  {internacao.status}
                </span>
              </div>

              <p className="text-sm text-gray-600">Motivo: {internacao.motivo || "-"}</p>
              <p className="text-sm text-gray-600">
                Entrada: {formatarDataHora(internacao.data_entrada)}
              </p>
              <p className="text-sm text-gray-600">
                Alta: {formatarDataHora(internacao.data_saida)}
              </p>
              {internacao.observacoes_alta && (
                <p className="text-sm text-green-700 mt-1">
                  Obs. alta: {internacao.observacoes_alta}
                </p>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                <InternacaoSubList
                  title="EvoluÃ§Ãµes"
                  items={internacao.evolucoes || []}
                  empty="Nenhuma evoluÃ§Ã£o."
                  renderItem={(ev) => (
                    <div
                      key={ev.id}
                      className="text-xs text-gray-700 border border-gray-200 bg-white rounded p-2"
                    >
                      <p className="text-gray-500">{formatarDataHora(ev.data_hora)}</p>
                      <p>
                        Temp: {ev.temperatura || "-"} â€¢ FC: {ev.freq_cardiaca || "-"} â€¢ FR:{" "}
                        {ev.freq_respiratoria || "-"}
                      </p>
                      {ev.observacoes && <p className="text-gray-600">{ev.observacoes}</p>}
                    </div>
                  )}
                />

                <InternacaoSubList
                  title="Procedimentos"
                  items={(internacao.procedimentos || []).slice(0, 8)}
                  empty="Nenhum procedimento."
                  renderItem={(proc, idx) => (
                    <div
                      key={`${proc.id || idx}_pet_proc`}
                      className="text-xs text-gray-700 border border-gray-200 bg-white rounded p-2"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <p className="font-semibold text-gray-800">
                          {proc.medicamento || "Procedimento"}
                        </p>
                        <span
                          className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${
                            proc.status === "agendado"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {proc.status === "agendado" ? "Agendado" : "ConcluÃ­do"}
                        </span>
                      </div>
                      <p>Agendado: {formatarDataHora(proc.horario_agendado)}</p>
                      <p>Executado: {formatarDataHora(proc.horario_execucao)}</p>
                      <p>
                        Dose: {proc.dose || "-"} â€¢ Via: {proc.via || "-"}
                      </p>
                      <p>ResponsÃ¡vel: {proc.executado_por || "-"}</p>
                      {proc.observacao_execucao && <p>Obs: {proc.observacao_execucao}</p>}
                    </div>
                  )}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
