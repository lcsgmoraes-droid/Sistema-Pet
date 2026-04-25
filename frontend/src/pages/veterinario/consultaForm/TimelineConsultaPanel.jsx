import { RefreshCw } from "lucide-react";
import { formatDateTimeBR } from "./consultaFormUtils";

export default function TimelineConsultaPanel({
  consultaIdAtual,
  carregandoTimeline,
  timelineConsulta,
  onRefresh,
  onOpenLink,
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Timeline clínica da consulta</h3>
          <p className="text-xs text-slate-500">
            Consulta, exames, vacinas, procedimentos, insumos e internações vinculados ficam centralizados aqui.
          </p>
        </div>
        {consultaIdAtual && (
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw size={14} />
            Atualizar timeline
          </button>
        )}
      </div>

      {!consultaIdAtual ? (
        <p className="mt-4 text-xs text-slate-500">Salve a consulta para começar a montar a timeline clínica.</p>
      ) : carregandoTimeline ? (
        <div className="mt-4 flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-b-2 border-slate-500" />
        </div>
      ) : timelineConsulta.length === 0 ? (
        <p className="mt-4 text-xs text-slate-500">Nenhum evento clínico vinculado ainda.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {timelineConsulta.map((evento) => (
            <div key={`${evento.kind}_${evento.item_id}`} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600">
                      {evento.kind.replaceAll("_", " ")}
                    </span>
                    {evento.status ? (
                      <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700">
                        {evento.status}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm font-semibold text-slate-900">{evento.titulo}</p>
                  <p className="text-xs text-slate-500">{formatDateTimeBR(evento.data_hora)}</p>
                  {evento.descricao ? <p className="mt-2 text-sm text-slate-600">{evento.descricao}</p> : null}
                  {Array.isArray(evento.meta?.insumos) && evento.meta.insumos.length > 0 ? (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {evento.meta.insumos.map((insumo, idx) => (
                        <span key={`${evento.kind}_${evento.item_id}_insumo_${idx}`} className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                          {insumo.nome || `Produto #${insumo.produto_id}`} • {insumo.quantidade} {insumo.unidade || "un"}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
                {evento.link ? (
                  <button
                    type="button"
                    onClick={() => onOpenLink(evento.link)}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100"
                  >
                    Abrir
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
