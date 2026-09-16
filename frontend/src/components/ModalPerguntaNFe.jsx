import { useState } from "react";
import { CheckCircle, FileText } from "lucide-react";
import { useDadosCupomEmpresa } from "../hooks/useDadosCupomEmpresa";
import { useFiscalDocumentAvailability } from "../hooks/useFiscalDocumentAvailability";
import { usePersistentBooleanState } from "../hooks/usePersistentBooleanState";
import { concluirVendaComCupom } from "../utils/pdvCupomFinalizacao";
import { ehVendaCrediario } from "../utils/pdvReceipt";
import { temPendenciasFiscais } from "../utils/nfeFiscalAssistida";
import { CupomImpressao } from "./ImprimirCupom";
import NfceCpfPrompt from "./pdv/NfceCpfPrompt";
import SeletorModeloDocumentoFiscal from "./SeletorModeloDocumentoFiscal";

const IMPRESSAO_CUPOM_STORAGE_KEY = "pdv_imprimir_cupom_ao_finalizar";
const IMPRESSAO_CREDIARIO_STORAGE_KEY = "pdv_imprimir_crediario_ao_finalizar";

export default function ModalPerguntaNFe({
  cliente,
  erro = "",
  loading = false,
  onConfirmar,
  onEmitir,
  venda,
  vendaId,
}) {
  const crediario = ehVendaCrediario(venda);
  const [imprimirCupom, setImprimirCupom] = usePersistentBooleanState(
    crediario ? IMPRESSAO_CREDIARIO_STORAGE_KEY : IMPRESSAO_CUPOM_STORAGE_KEY,
    crediario,
  );
  const [tipoNota, setTipoNota] = useState("nfce");
  const [nfceCpfResolved, setNfceCpfResolved] = useState(
    Boolean(cliente?.cpf || cliente?.cnpj || cliente?.cpf_cnpj),
  );
  const [savedCustomerDocument, setSavedCustomerDocument] = useState("");
  const { carregandoEmpresa, dadosEmpresa } = useDadosCupomEmpresa();
  const {
    reload: reloadFiscalStatus,
    resolvePending,
    statuses: fiscalStatuses,
  } = useFiscalDocumentAvailability(vendaId);
  const clienteIdentificado = Boolean(
    cliente?.cpf || cliente?.cnpj || cliente?.cpf_cnpj || savedCustomerDocument,
  );
  const selectedFiscalStatus = fiscalStatuses[tipoNota] || {};
  const selectedModelBlocked = Boolean(
    selectedFiscalStatus.loading ||
    selectedFiscalStatus.error ||
    temPendenciasFiscais(selectedFiscalStatus.validation) ||
    (tipoNota === "nfe" && !clienteIdentificado) ||
    (tipoNota === "nfce" && !nfceCpfResolved),
  );

  const handleFinalizar = () => {
    concluirVendaComCupom({
      imprimirCupom,
      onConcluir: onConfirmar,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="mx-4 max-h-[92dvh] w-full max-w-md overflow-y-auto rounded-lg bg-white shadow-xl">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">Venda Finalizada!</h3>
              <p className="text-sm text-gray-500">
                Escolha se deseja emitir um documento fiscal antes de finalizar.
              </p>
            </div>
          </div>

          {erro && (
            <div className="mb-4 whitespace-pre-line rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {erro}
            </div>
          )}

          <div className="space-y-3">
            <SeletorModeloDocumentoFiscal
              clienteIdentificado={clienteIdentificado}
              disabled={loading}
              fiscalStatuses={fiscalStatuses}
              onChange={setTipoNota}
              onResolvePending={resolvePending}
              onRetryValidation={reloadFiscalStatus}
              value={tipoNota}
            />

            <NfceCpfPrompt
              cliente={cliente}
              disabled={loading}
              onResolvedChange={setNfceCpfResolved}
              onSaved={(updatedCustomer) => {
                setSavedCustomerDocument(updatedCustomer?.cpf || "cpf-salvo");
                reloadFiscalStatus();
              }}
              visible={tipoNota === "nfce"}
            />

            {(loading || !selectedModelBlocked) && (
              <button
                type="button"
                onClick={() => onEmitir(tipoNota)}
                disabled={loading}
                className={`flex w-full items-center justify-center space-x-2 rounded-lg px-4 py-3 font-medium text-white transition-colors disabled:opacity-50 ${
                  tipoNota === "nfce"
                    ? "bg-green-600 hover:bg-green-700"
                    : "bg-blue-600 hover:bg-blue-700"
                }`}
              >
                <FileText className="h-5 w-5" />
                <span>
                  {loading
                    ? "Aguardando autorização da SEFAZ..."
                    : `Emitir ${tipoNota === "nfce" ? "NFC-e" : "NF-e"}`}
                </span>
              </button>
            )}

            {loading && (
              <p className="text-center text-xs text-gray-500" role="status">
                Normalmente leva alguns segundos. Mantenha esta janela aberta enquanto o CorePet
                acompanha o retorno da SEFAZ.
              </p>
            )}

            <button
              type="button"
              onClick={handleFinalizar}
              disabled={loading || (imprimirCupom && carregandoEmpresa)}
              className="flex w-full items-center justify-center space-x-2 rounded-lg bg-gray-100 px-4 py-3 font-medium text-gray-700 transition-colors hover:bg-gray-200 disabled:opacity-50"
            >
              <CheckCircle className="h-5 w-5" />
              <span>Finalizar</span>
            </button>

            <label
              className="flex cursor-pointer items-center justify-center gap-1.5 px-1 text-[11px] text-gray-400"
              title="Esta preferência fica salva neste computador"
            >
              <input
                type="checkbox"
                checked={imprimirCupom}
                onChange={(event) => setImprimirCupom(event.target.checked)}
                disabled={loading}
                className="h-3.5 w-3.5 rounded border-gray-300 text-gray-500 focus:ring-1 focus:ring-gray-400 disabled:opacity-50"
              />
              <span>
                {crediario
                  ? "Imprimir comprovante de crediário em 2 vias"
                  : "Imprimir recibo do PDV ao concluir"}
              </span>
            </label>
          </div>

          <CupomImpressao empresa={dadosEmpresa} portal venda={venda} />
        </div>
      </div>
    </div>
  );
}
