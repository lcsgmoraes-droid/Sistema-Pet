import { Bot, Loader2, Send, X } from "lucide-react";

const SUGESTOES_INICIAIS = [
  "O que ele comprou na última vez?",
  "Quantas vezes comprou ração?",
  "Tem alguma alergia?",
];

export default function PDVAssistenteSidebar({
  aberto,
  clienteNome,
  onClose,
  mensagensAssistente,
  enviandoAssistente,
  chatAssistenteEndRef,
  inputAssistente,
  setInputAssistente,
  enviarMensagemAssistente,
}) {
  if (!aberto) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute top-0 right-0 w-96 h-full bg-white border-l border-indigo-200 shadow-xl flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-indigo-200 bg-indigo-600 text-white">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5" />
            <div>
              <h2 className="text-sm font-semibold">Assistente IA</h2>
              <p className="text-xs text-indigo-200">{clienteNome}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-indigo-500 rounded transition-colors"
            type="button"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-gray-50">
          {mensagensAssistente.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-400">
                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                <p className="text-xs">Carregando histórico...</p>
              </div>
            </div>
          )}

          {mensagensAssistente.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] px-3 py-2 rounded-lg text-xs leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-indigo-600 text-white rounded-br-none"
                    : "bg-white border border-gray-200 text-gray-800 rounded-bl-none shadow-sm"
                }`}
              >
                {msg.texto}
              </div>
            </div>
          ))}

          {enviandoAssistente && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 text-gray-400 px-3 py-2 rounded-lg rounded-bl-none text-xs flex items-center gap-1 shadow-sm">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>Pensando...</span>
              </div>
            </div>
          )}

          <div ref={chatAssistenteEndRef} />
        </div>

        {mensagensAssistente.length === 1 && (
          <div className="px-3 py-2 border-t border-gray-100 bg-gray-50 flex flex-wrap gap-1">
            {SUGESTOES_INICIAIS.map((sugestao) => (
              <button
                key={sugestao}
                onClick={() => setInputAssistente(sugestao)}
                className="text-[10px] px-2 py-1 bg-indigo-50 border border-indigo-200 text-indigo-600 rounded-full hover:bg-indigo-100 transition-colors"
                type="button"
              >
                {sugestao}
              </button>
            ))}
          </div>
        )}

        <div className="p-3 border-t border-gray-200 bg-white">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputAssistente}
              onChange={(e) => setInputAssistente(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  enviarMensagemAssistente();
                }
              }}
              placeholder="Pergunta sobre o cliente..."
              disabled={enviandoAssistente}
              className="flex-1 text-xs px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 disabled:opacity-50"
              autoFocus
            />
            <button
              onClick={enviarMensagemAssistente}
              disabled={!inputAssistente.trim() || enviandoAssistente}
              className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              type="button"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
