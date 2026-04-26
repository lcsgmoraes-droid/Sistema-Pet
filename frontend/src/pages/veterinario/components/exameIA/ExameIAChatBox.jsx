import { Send } from "lucide-react";

export default function ExameIAChatBox({
  carregando,
  chatFimRef,
  historico,
  onEnviar,
  onKeyDown,
  pergunta,
  placeholder = "Digite sua pergunta sobre o exame...",
  setPergunta,
  textoVazio,
}) {
  return (
    <>
      {historico.length > 0 && (
        <div className="max-h-56 space-y-2 overflow-y-auto rounded-lg border border-indigo-100 bg-white p-3">
          {historico.map((mensagem, index) => (
            <div key={index} className={`flex ${mensagem.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                  mensagem.role === "user"
                    ? "rounded-br-none bg-indigo-600 text-white"
                    : "rounded-bl-none bg-gray-100 text-gray-800"
                }`}
              >
                {mensagem.role === "ia" && (
                  <span className="mb-0.5 block text-xs font-semibold text-indigo-500">IA</span>
                )}
                {mensagem.text}
              </div>
            </div>
          ))}
          {carregando && (
            <div className="flex justify-start">
              <div className="animate-pulse rounded-xl rounded-bl-none bg-gray-100 px-3 py-2 text-sm text-gray-500">
                Analisando...
              </div>
            </div>
          )}
          <div ref={chatFimRef} />
        </div>
      )}

      {historico.length === 0 && (
        <p className="text-xs italic text-indigo-500">{textoVazio}</p>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={pergunta}
          onChange={(event) => setPergunta(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          disabled={carregando}
          className="flex-1 rounded-lg border border-indigo-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:opacity-60"
        />
        <button
          type="button"
          onClick={onEnviar}
          disabled={!pergunta.trim() || carregando}
          className="flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-2 text-sm text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
        >
          <Send size={14} />
        </button>
      </div>
    </>
  );
}
