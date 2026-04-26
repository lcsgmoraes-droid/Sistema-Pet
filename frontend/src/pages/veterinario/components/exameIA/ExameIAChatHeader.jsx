import { Bot } from "lucide-react";

export default function ExameIAChatHeader({ expandido, quantidadeExames, onToggle }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-indigo-100"
    >
      <div className="flex items-center gap-2">
        <Bot size={18} className="text-indigo-500" />
        <span className="text-sm font-semibold text-indigo-800">Exames do paciente + IA</span>
        {quantidadeExames > 0 && (
          <span className="rounded-full bg-indigo-200 px-2 py-0.5 text-xs text-indigo-700">
            {quantidadeExames} exame{quantidadeExames !== 1 ? "s" : ""}
          </span>
        )}
      </div>
      <span className="text-xs text-indigo-500">{expandido ? "fechar" : "abrir"}</span>
    </button>
  );
}
