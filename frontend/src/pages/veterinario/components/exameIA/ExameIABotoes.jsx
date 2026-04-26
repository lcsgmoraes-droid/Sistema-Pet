import { FlaskConical } from "lucide-react";

export default function ExameIABotoes({
  consultaId,
  onAbrirConsulta,
  onNovoExame,
  onProcessar,
  processando,
  temAnaliseIA,
  temArquivo,
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {typeof onNovoExame === "function" && (
        <button
          type="button"
          onClick={onNovoExame}
          className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-white px-3 py-2 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
        >
          <FlaskConical size={14} />
          Novo exame / anexar
        </button>
      )}
      {typeof onProcessar === "function" && (
        <button
          type="button"
          onClick={onProcessar}
          disabled={processando}
          className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-600 px-3 py-2 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          {processando
            ? "Processando..."
            : temArquivo
              ? temAnaliseIA
                ? "Reprocessar arquivo + IA"
                : "Processar arquivo + IA"
              : "Interpretar resultado"}
        </button>
      )}
      {typeof onAbrirConsulta === "function" && (
        <button
          type="button"
          onClick={onAbrirConsulta}
          className="inline-flex items-center gap-2 rounded-lg border border-orange-200 bg-white px-3 py-2 text-xs font-medium text-orange-700 hover:bg-orange-50"
        >
          {consultaId ? `Abrir consulta #${consultaId}` : "Abrir consulta"}
        </button>
      )}
    </div>
  );
}
