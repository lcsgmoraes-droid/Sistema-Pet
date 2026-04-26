import { ThumbsDown, ThumbsUp } from "lucide-react";

export default function AssistenteIAHistorico({
  carregandoHistorico,
  historico,
  onEnviarFeedback,
  salvandoFeedbackId,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <h2 className="text-sm font-semibold text-gray-700">Conversa</h2>
      {carregandoHistorico && (
        <p className="text-xs text-gray-400">Carregando histórico...</p>
      )}

      {historico.length === 0 ? (
        <p className="text-sm text-gray-400">Ainda sem mensagens. Envie a primeira pergunta.</p>
      ) : (
        <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
          {historico.map((msg, index) => (
            <div
              key={msg.id || msg.localId || `${msg.role}-${index}`}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[88%] px-3 py-2 rounded-xl text-sm whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-cyan-600 text-white rounded-br-none"
                    : "bg-gray-100 text-gray-800 rounded-bl-none"
                }`}
              >
                {msg.role === "ia" && (
                  <div className="text-[11px] font-semibold text-cyan-700 mb-1">IA Vet</div>
                )}
                {msg.text}

                {msg.role === "ia" && msg.id ? (
                  <div className="mt-2 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => onEnviarFeedback(msg.id, true)}
                      disabled={salvandoFeedbackId === String(msg.id)}
                      className={`inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md border ${
                        msg.feedback?.util === true
                          ? "border-green-400 text-green-700 bg-green-50"
                          : "border-gray-200 text-gray-600"
                      }`}
                    >
                      <ThumbsUp size={11} /> Útil
                    </button>
                    <button
                      type="button"
                      onClick={() => onEnviarFeedback(msg.id, false)}
                      disabled={salvandoFeedbackId === String(msg.id)}
                      className={`inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md border ${
                        msg.feedback?.util === false
                          ? "border-amber-400 text-amber-700 bg-amber-50"
                          : "border-gray-200 text-gray-600"
                      }`}
                    >
                      <ThumbsDown size={11} /> Não útil
                    </button>
                  </div>
                ) : null}

                {msg.role === "ia" && msg.feedback?.comentario ? (
                  <div className="mt-2 text-[11px] text-gray-500 border-t border-gray-200 pt-2">
                    Comentário: {msg.feedback.comentario}
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
