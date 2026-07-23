import { Bot } from "lucide-react";
import { getMemoriaAssistenteIABadge } from "./assistenteIAUtils";

export default function AssistenteIAHeader({ conhecimentoStatus, memoriaAtiva }) {
  const memoriaBadge = getMemoriaAssistenteIABadge(memoriaAtiva);
  const documentos = conhecimentoStatus?.documentos;

  return (
    <div className="flex items-center gap-3">
      <div className="p-2 bg-cyan-100 rounded-xl">
        <Bot size={20} className="text-cyan-700" />
      </div>
      <div>
        <h1 className="text-xl font-bold text-gray-800">Assistente IA Veterinário</h1>
        <p className="text-xs text-gray-500">
          Copiloto clínico com literatura atualizada e memória de feedback isolada por usuário e
          clínica.
        </p>
      </div>
      <div className="ml-auto flex flex-wrap justify-end gap-2">
        {documentos ? (
          <span
            className={`text-xs px-2 py-1 rounded-full ${
              (documentos.aprovados || 0) + (documentos.automaticos_disponiveis || 0) > 0
                ? "bg-cyan-100 text-cyan-800"
                : "bg-amber-100 text-amber-800"
            }`}
          >
            {(documentos.automaticos_disponiveis || 0) + (documentos.aprovados || 0)} evidência(s)
            disponível(is)
            {documentos.referencias_sem_resumo
              ? ` • ${documentos.referencias_sem_resumo} apenas como referência`
              : ""}
          </span>
        ) : null}
        <span className={`text-xs px-2 py-1 rounded-full ${memoriaBadge.className}`}>
          {memoriaBadge.label}
        </span>
      </div>
    </div>
  );
}
