import { XCircle } from "lucide-react";

import CustomerIdentity from "../../components/ui/CustomerIdentity";

export default function NFSaidaCancelamentoModal({
  modalCancelar,
  setModalCancelar,
  justificativa,
  setJustificativa,
  cancelando,
  cancelarNota,
}) {
  if (!modalCancelar) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full m-4">
        <div className="bg-red-50 border-b px-6 py-4 flex items-center gap-3">
          <XCircle className="w-6 h-6 text-red-600" />
          <h3 className="text-xl font-bold text-gray-800">Cancelar Nota Fiscal</h3>
        </div>
        <div className="p-6 space-y-4">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
            <strong>Atenção:</strong> O cancelamento é irreversível e será enviado para a SEFAZ.
          </div>
          <div>
            <p className="text-sm text-gray-600">
              <strong>Nota:</strong> #{modalCancelar.numero} — Série {modalCancelar.serie}
            </p>
            <p className="text-sm text-gray-600">
              <strong>Cliente:</strong>{" "}
              <CustomerIdentity
                code={
                  modalCancelar.cliente?.codigo ||
                  modalCancelar.cliente_id ||
                  modalCancelar.cliente?.id
                }
                customer={modalCancelar.cliente}
                fallback="N/A"
                layout="inline"
              />
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Justificativa *</label>
            <textarea
              value={justificativa}
              onChange={(event) => setJustificativa(event.target.value)}
              placeholder="Digite o motivo do cancelamento (mínimo 15 caracteres)"
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
            />
            <p className="text-xs text-gray-500 mt-1">{justificativa.length}/15 caracteres</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                setModalCancelar(null);
                setJustificativa("");
              }}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              disabled={cancelando}
            >
              Voltar
            </button>
            <button
              onClick={cancelarNota}
              disabled={cancelando || justificativa.length < 15}
              className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {cancelando ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />{" "}
                  Cancelando...
                </>
              ) : (
                <>
                  <XCircle className="w-5 h-5" /> Confirmar Cancelamento
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
