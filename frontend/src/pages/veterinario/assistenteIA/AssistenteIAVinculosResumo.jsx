import { Link2 } from "lucide-react";

export default function AssistenteIAVinculosResumo({ consultaSelecionada, exameSelecionado, onAbrirConsulta }) {
  if (!consultaSelecionada && !exameSelecionado) return null;

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {consultaSelecionada && (
        <ConsultaVinculadaCard consultaSelecionada={consultaSelecionada} onAbrirConsulta={onAbrirConsulta} />
      )}

      {exameSelecionado && <ExameVinculadoCard exameSelecionado={exameSelecionado} />}
    </div>
  );
}

function ConsultaVinculadaCard({ consultaSelecionada, onAbrirConsulta }) {
  return (
    <div className="rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-cyan-900">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-cyan-600">Consulta vinculada</p>
          <p className="font-semibold">#{consultaSelecionada.id}</p>
          <p className="text-xs text-cyan-700">{consultaSelecionada.motivo_consulta || "Sem motivo informado"}</p>
        </div>
        <button
          type="button"
          onClick={() => onAbrirConsulta(consultaSelecionada.id)}
          className="inline-flex items-center gap-2 rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-medium text-cyan-700 hover:bg-cyan-100"
        >
          <Link2 size={13} />
          Abrir consulta
        </button>
      </div>
    </div>
  );
}

function ExameVinculadoCard({ exameSelecionado }) {
  return (
    <div className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-900">
      <p className="text-xs font-medium uppercase tracking-wide text-violet-600">Exame vinculado</p>
      <p className="font-semibold">
        #{exameSelecionado.id} • {exameSelecionado.nome || exameSelecionado.tipo || "Exame"}
      </p>
      <p className="text-xs text-violet-700">
        {exameSelecionado.arquivo_nome ? `Arquivo: ${exameSelecionado.arquivo_nome}` : "Sem arquivo anexado ainda"}
      </p>
    </div>
  );
}
