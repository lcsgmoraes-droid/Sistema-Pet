import { Download, Link2 } from "lucide-react";

export default function AgendaCalendarioCard({
  calendarioMeta,
  carregandoCalendario,
  mensagemCalendario,
  onBaixarCalendario,
  onCopiarLink,
}) {
  return (
    <div className="rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-cyan-900">Agenda no celular</h2>
          <p className="mt-1 text-sm text-cyan-800">
            Assine sua agenda veterinária no calendário do celular com um link privado ou baixe um arquivo .ics.
          </p>
          {calendarioMeta?.mensagem_escopo && (
            <p className="mt-2 text-xs text-cyan-700">{calendarioMeta.mensagem_escopo}</p>
          )}
          {mensagemCalendario && (
            <p className="mt-2 text-xs font-medium text-cyan-700">{mensagemCalendario}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onBaixarCalendario}
            className="inline-flex items-center gap-2 rounded-lg border border-cyan-300 bg-white px-3 py-2 text-sm font-medium text-cyan-800 hover:bg-cyan-100"
          >
            <Download size={14} />
            Baixar .ics
          </button>
          <button
            type="button"
            onClick={onCopiarLink}
            disabled={carregandoCalendario || !calendarioMeta?.feed_url}
            className="inline-flex items-center gap-2 rounded-lg border border-cyan-300 bg-white px-3 py-2 text-sm font-medium text-cyan-800 hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Link2 size={14} />
            Copiar link privado
          </button>
        </div>
      </div>
    </div>
  );
}
