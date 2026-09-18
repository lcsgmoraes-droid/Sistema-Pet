import { useState } from "react";
import { FileText, HelpCircle, X } from "lucide-react";
import { useFiscalDocumentAvailability } from "../../hooks/useFiscalDocumentAvailability";
import { documentoCpfCnpjCliente } from "../../utils/cpf";
import { temPendenciasFiscais } from "../../utils/nfeFiscalAssistida";
import NfceCpfPrompt from "./NfceCpfPrompt";
import SeletorModeloDocumentoFiscal from "../SeletorModeloDocumentoFiscal";

export default function ModalSelecaoDocumentoFiscal({ cliente, onClose, onEmitir, vendaId }) {
  const documentoCliente = documentoCpfCnpjCliente(cliente);
  const [tipoNota, setTipoNota] = useState("nfce");
  const [emitindo, setEmitindo] = useState(false);
  const [nfceCpfResolved, setNfceCpfResolved] = useState(Boolean(documentoCliente));
  const [savedCustomerDocument, setSavedCustomerDocument] = useState("");
  const [headerHelpOpen, setHeaderHelpOpen] = useState(false);
  const clienteIdentificado = Boolean(documentoCliente || savedCustomerDocument);
  const {
    reload: reloadFiscalStatus,
    resolvePending,
    statuses: fiscalStatuses,
  } = useFiscalDocumentAvailability(vendaId);
  const selectedFiscalStatus = fiscalStatuses[tipoNota] || {};
  const selectedModelBlocked = Boolean(
    selectedFiscalStatus.loading ||
    selectedFiscalStatus.error ||
    temPendenciasFiscais(selectedFiscalStatus.validation) ||
    (tipoNota === "nfe" && !clienteIdentificado) ||
    (tipoNota === "nfce" && !nfceCpfResolved),
  );

  const handleEmitir = async () => {
    setEmitindo(true);
    try {
      const emitida = await onEmitir(tipoNota);
      if (emitida) {
        onClose();
      }
    } finally {
      setEmitindo(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-modelo-documento-fiscal"
        className="w-full max-w-lg rounded-2xl bg-white shadow-2xl"
      >
        <div className="flex items-start justify-between border-b border-gray-100 px-6 py-5">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <h2 id="titulo-modelo-documento-fiscal" className="text-lg font-bold text-gray-900">
                Escolha o documento fiscal
              </h2>
              <button
                type="button"
                onClick={() => setHeaderHelpOpen((open) => !open)}
                aria-label="Explicação sobre os documentos fiscais"
                aria-expanded={headerHelpOpen}
                aria-controls="ajuda-modelos-fiscais"
                className="rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
              >
                <HelpCircle className="h-4 w-4" />
              </button>
            </div>
            {headerHelpOpen && (
              <p id="ajuda-modelos-fiscais" className="mt-1 text-sm text-gray-500">
                A NFC-e já vem selecionada por ser a opção mais comum no caixa.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={emitindo}
            aria-label="Fechar"
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700 disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-6 py-5">
          <SeletorModeloDocumentoFiscal
            clienteIdentificado={clienteIdentificado}
            disabled={emitindo}
            fiscalStatuses={fiscalStatuses}
            onChange={setTipoNota}
            onResolvePending={resolvePending}
            onRetryValidation={reloadFiscalStatus}
            value={tipoNota}
          />
          <div className="mt-3">
            <NfceCpfPrompt
              cliente={cliente}
              disabled={emitindo}
              onContinueWithoutCpf={handleEmitir}
              onResolvedChange={setNfceCpfResolved}
              onSaved={(updatedCustomer) => {
                setSavedCustomerDocument(updatedCustomer?.cpf || "cpf-salvo");
                reloadFiscalStatus();
              }}
              visible={tipoNota === "nfce"}
            />
          </div>
          {emitindo && (
            <p className="mt-4 text-center text-xs text-gray-500" role="status">
              Normalmente leva alguns segundos. Mantenha esta janela aberta enquanto o CorePet
              acompanha o retorno da SEFAZ.
            </p>
          )}
        </div>

        <div className="flex flex-col-reverse gap-2 border-t border-gray-100 px-6 py-4 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={emitindo}
            className="rounded-lg border border-gray-300 px-4 py-2.5 font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Voltar
          </button>
          {(emitindo || !selectedModelBlocked) && (
            <button
              type="button"
              onClick={handleEmitir}
              disabled={emitindo}
              className={`flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 font-semibold text-white disabled:opacity-50 ${
                tipoNota === "nfce"
                  ? "bg-green-600 hover:bg-green-700"
                  : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              <FileText className="h-5 w-5" />
              {emitindo
                ? "Aguardando autorização da SEFAZ..."
                : `Emitir ${tipoNota === "nfce" ? "NFC-e (65)" : "NF-e (55)"}`}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
