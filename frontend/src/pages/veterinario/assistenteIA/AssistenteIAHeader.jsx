import { Bot } from "lucide-react";
import { getMemoriaAssistenteIABadge } from "./assistenteIAUtils";

export default function AssistenteIAHeader({ memoriaAtiva }) {
  const memoriaBadge = getMemoriaAssistenteIABadge(memoriaAtiva);

  return (
    <div className="flex items-center gap-3">
      <div className="p-2 bg-cyan-100 rounded-xl">
        <Bot size={20} className="text-cyan-700" />
      </div>
      <div>
        <h1 className="text-xl font-bold text-gray-800">Assistente IA Veterinário</h1>
        <p className="text-xs text-gray-500">
          Aba dedicada para cálculo de dose, interação medicamentosa e discussão clínica.
        </p>
      </div>
      <div className="ml-auto">
        <span className={`text-xs px-2 py-1 rounded-full ${memoriaBadge.className}`}>
          {memoriaBadge.label}
        </span>
      </div>
    </div>
  );
}
