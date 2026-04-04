export default function CampanhasLoteModal({
  modalLote,
  setModalLote,
  loteForm,
  setLoteForm,
  resultadoLote,
  enviarLote,
  enviandoLote,
}) {
  if (!modalLote) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Envio em lote</h3>
          <button
            onClick={() => setModalLote(false)}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            x
          </button>
        </div>
        <div className="px-6 py-4 space-y-3">
          <div>
            <label
              htmlFor="lote-nivel"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Nivel de ranking
            </label>
            <select
              id="lote-nivel"
              value={loteForm.nivel}
              onChange={(e) =>
                setLoteForm((p) => ({ ...p, nivel: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              <option value="todos">Todos os niveis</option>
              <option value="platinum">Diamante</option>
              <option value="diamond">Platina</option>
              <option value="gold">Ouro</option>
              <option value="silver">Prata</option>
              <option value="bronze">Bronze</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="lote-assunto"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Assunto do email
            </label>
            <input
              id="lote-assunto"
              type="text"
              placeholder="Ex: Promocao exclusiva para clientes Ouro"
              value={loteForm.assunto}
              onChange={(e) =>
                setLoteForm((p) => ({ ...p, assunto: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label
              htmlFor="lote-msg"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Mensagem
            </label>
            <textarea
              id="lote-msg"
              rows={4}
              placeholder="Escreva a mensagem que sera enviada para os clientes..."
              value={loteForm.mensagem}
              onChange={(e) =>
                setLoteForm((p) => ({ ...p, mensagem: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          {resultadoLote && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm">
              <p className="font-semibold text-green-800">
                {resultadoLote.enfileirados} email(s) enfileirados.
              </p>
              {resultadoLote.sem_email > 0 && (
                <p className="text-green-600">
                  {resultadoLote.sem_email} cliente(s) sem email foram
                  ignorados.
                </p>
              )}
            </div>
          )}
        </div>
        <div className="px-6 py-4 border-t flex gap-3 justify-end">
          <button
            onClick={() => setModalLote(false)}
            className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
          >
            Fechar
          </button>
          <button
            onClick={enviarLote}
            disabled={enviandoLote}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {enviandoLote ? "Enviando..." : "Enfileirar envio"}
          </button>
        </div>
      </div>
    </div>
  );
}
