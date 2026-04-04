export default function CampanhasEnvioInativosModal({
  modalEnvioInativos,
  setModalEnvioInativos,
  resultadoEnvioInativos,
  setResultadoEnvioInativos,
  envioInativosForm,
  setEnvioInativosForm,
  enviandoInativos,
  enviarParaInativos,
}) {
  if (!modalEnvioInativos) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">
              Enviar email de reativacao
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Clientes sem compra ha mais de {modalEnvioInativos} dias. Os
              emails sao enfileirados e enviados em lotes.
            </p>
          </div>
          <button
            onClick={() => {
              setModalEnvioInativos(null);
              setResultadoEnvioInativos(null);
            }}
            className="text-gray-400 hover:text-gray-600 text-xl font-bold"
          >
            x
          </button>
        </div>
        <div className="p-6 space-y-4">
          {resultadoEnvioInativos ? (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-1">
              <p className="font-semibold text-green-800">
                Emails enfileirados com sucesso.
              </p>
              <p className="text-sm text-green-700">
                {resultadoEnvioInativos.enfileirados} email(s) adicionados a
                fila.
              </p>
              {resultadoEnvioInativos.sem_email > 0 && (
                <p className="text-xs text-gray-500">
                  {resultadoEnvioInativos.sem_email} cliente(s) sem email
                  cadastrado foram ignorados.
                </p>
              )}
              <button
                onClick={() => {
                  setModalEnvioInativos(null);
                  setResultadoEnvioInativos(null);
                }}
                className="mt-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
              >
                Fechar
              </button>
            </div>
          ) : (
            <>
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase block mb-1">
                  Assunto do email
                </label>
                <input
                  type="text"
                  value={envioInativosForm.assunto}
                  onChange={(e) =>
                    setEnvioInativosForm((f) => ({
                      ...f,
                      assunto: e.target.value,
                    }))
                  }
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
                  placeholder="Ex: Sentimos sua falta"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase block mb-1">
                  Mensagem
                </label>
                <textarea
                  rows={5}
                  value={envioInativosForm.mensagem}
                  onChange={(e) =>
                    setEnvioInativosForm((f) => ({
                      ...f,
                      mensagem: e.target.value,
                    }))
                  }
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300 resize-none"
                  placeholder="Escreva a mensagem para os clientes inativos..."
                />
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  onClick={() => setModalEnvioInativos(null)}
                  className="flex-1 py-2.5 border border-gray-200 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  onClick={enviarParaInativos}
                  disabled={
                    enviandoInativos ||
                    !envioInativosForm.assunto.trim() ||
                    !envioInativosForm.mensagem.trim()
                  }
                  className="flex-1 py-2.5 bg-orange-500 text-white rounded-lg text-sm font-semibold hover:bg-orange-600 disabled:opacity-50 transition-colors"
                >
                  {enviandoInativos ? "Enfileirando..." : "Enfileirar emails"}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
