import { CheckCircle, FileText, Printer } from "lucide-react";
import { usePersistentBooleanState } from "../hooks/usePersistentBooleanState";
import { concluirVendaComCupom } from "../utils/pdvCupomFinalizacao";
import { CupomImpressao } from "./ImprimirCupom";

const IMPRESSAO_CUPOM_STORAGE_KEY = "pdv_imprimir_cupom_ao_finalizar";

export default function ModalPerguntaNFe({
  cliente,
  erro = "",
  loading = false,
  onConfirmar,
  onEmitir,
  venda,
}) {
  const [imprimirCupom, setImprimirCupom] = usePersistentBooleanState(
    IMPRESSAO_CUPOM_STORAGE_KEY,
    false,
  );

  const handleEmitirCupomFiscal = () => {
    concluirVendaComCupom({
      imprimirCupom,
      onConcluir: onConfirmar,
    });
  };

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

            <label className="flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
              <span className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <Printer className="h-4 w-4" />
                Imprimir automaticamente neste computador
              </span>
              <input
                type="checkbox"
                checked={imprimirCupom}
                onChange={(event) => setImprimirCupom(event.target.checked)}
                disabled={loading}
                className="h-5 w-5 rounded border-gray-300 text-green-600 focus:ring-green-500 disabled:opacity-50"
              />
            </label>

            <button
              onClick={handleEmitirCupomFiscal}
              disabled={loading}
              className="flex w-full items-center justify-center space-x-2 rounded-lg bg-gray-100 px-4 py-3 font-medium text-gray-700 transition-colors hover:bg-gray-200 disabled:opacity-50"
            >
              <Printer className="h-5 w-5" />
              <span>Emitir cupom fiscal</span>
            </button>
          </div>

          <p className="text-xs text-gray-500 text-center mt-4">
            Com a opção desmarcada, o botão apenas encerra e sai da venda.
          </p>

          <CupomImpressao venda={venda} />
        </div>
      </div>
    </div>
  );
}
