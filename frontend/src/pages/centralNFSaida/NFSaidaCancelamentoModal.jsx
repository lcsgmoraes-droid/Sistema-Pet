import { XCircle } from "lucide-react";

import CustomerIdentity from "../../components/ui/CustomerIdentity";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";
import { obterPendenciaCancelamentoFiscal } from "../../utils/pdvFiscalStatus";

export default function NFSaidaCancelamentoModal({
  modalCancelar,
  setModalCancelar,
  justificativa,
  setJustificativa,
  cancelando,
  cancelarNota,
}) {
  if (!modalCancelar) return null;
  const pendenciaFiscal = obterPendenciaCancelamentoFiscal({
    ...modalCancelar,
    status: modalCancelar.venda_status,
    nfe_status: modalCancelar.status,
  });

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="cancelar-nota-titulo"
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full m-4">
        <div className="bg-red-50 border-b px-6 py-4 flex items-center gap-3">
          <XCircle className="w-6 h-6 text-red-600" />
          <h3 id="cancelar-nota-titulo" className="text-xl font-bold text-gray-800">
            Cancelar Nota Fiscal
          </h3>
        </div>
        <div className="p-6 space-y-4">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
            <strong>Atenção:</strong> O cancelamento é irreversível e será enviado para a SEFAZ.
          </div>
          {pendenciaFiscal && (
            <div
              role="alert"
              className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-600 dark:bg-amber-950 dark:text-amber-100"
            >
              <strong>{pendenciaFiscal.label}</strong>
              {pendenciaFiscal.detalhe && <p className="mt-1">{pendenciaFiscal.detalhe}</p>}
            </div>
          )}
          <div>
            <p className="text-sm text-gray-600">
              <strong>Nota:</strong> #{modalCancelar.numero} — Série {modalCancelar.serie}
            </p>
            <p className="text-sm text-gray-600">
              <strong>Cliente:</strong>{" "}
              <CustomerIdentity customer={modalCancelar.cliente} fallback="N/A" layout="inline" />
            </p>
          </div>
          <InputTextoLongo
            label="Justificativa"
            required
            value={justificativa}
            onChange={setJustificativa}
            placeholder="Digite o motivo do cancelamento (mínimo 15 caracteres)"
            linhas={4}
            help={`${justificativa.length}/15 caracteres`}
          />
          <div className="flex gap-2">
            <BotaoCancelar
              onClick={() => {
                setModalCancelar(null);
                setJustificativa("");
              }}
              disabled={cancelando}
            >
              Voltar
            </BotaoCancelar>
            <BotaoInteracao
              onClick={cancelarNota}
              disabled={cancelando || justificativa.length < 15}
              icon={XCircle}
              loading={cancelando}
            >
              {cancelando ? "Enviando..." : "Confirmar Cancelamento"}
            </BotaoInteracao>
          </div>
        </div>
      </div>
    </div>
  );
}
