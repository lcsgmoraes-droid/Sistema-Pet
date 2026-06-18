import { CheckCircle, FileText } from "lucide-react";

export default function ModalPerguntaNFe({
  cliente,
  erro = "",
  loading = false,
  onConfirmar,
  onEmitir,
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">Venda Finalizada!</h3>
              <p className="text-sm text-gray-500">Deseja emitir nota fiscal?</p>
            </div>
          </div>

          {erro && (
            <div className="mb-4 whitespace-pre-line rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {erro}
            </div>
          )}

          <div className="space-y-3">
            {cliente?.cnpj ? (
              <>
                <button
                  onClick={() => onEmitir("nfe")}
                  disabled={loading}
                  className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  <FileText className="w-5 h-5" />
                  <span>Emitir NF-e (Empresa)</span>
                </button>
                <button
                  onClick={() => onEmitir("nfce")}
                  disabled={loading}
                  className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  <FileText className="w-5 h-5" />
                  <span>Emitir NFC-e (Cupom)</span>
                </button>
              </>
            ) : (
              <button
                onClick={() => onEmitir("nfce")}
                disabled={loading}
                className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                <FileText className="w-5 h-5" />
                <span>Emitir NFC-e</span>
              </button>
            )}

            <button
              onClick={onConfirmar}
              disabled={loading}
              className="w-full px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              Não emitir agora
            </button>
          </div>

          <p className="text-xs text-gray-500 text-center mt-4">
            Você pode emitir a nota fiscal depois na tela de vendas
          </p>
        </div>
      </div>
    </div>
  );
}
