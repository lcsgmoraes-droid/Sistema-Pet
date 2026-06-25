import { AlertTriangle, Save, Trash2, X } from "lucide-react";
import ActionButton from "../../components/ui/ActionButton";
import CopyableCode from "../../components/ui/CopyableCode";
import { REQUEST_STATUS, REQUEST_TYPE_LABEL } from "./lgpdConstants";
import { formatDate } from "./lgpdUtils";

export default function LGPDRequestModal({
  abrirDialogAnonimizacao,
  canAnonymizeSelected,
  processForm,
  processarSolicitacao,
  requestModalOpen,
  requestToProcess,
  saving,
  setProcessForm,
  setRequestModalOpen,
}) {
  if (!requestModalOpen || !requestToProcess) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div className="flex max-h-[92vh] w-full max-w-3xl flex-col rounded-lg bg-white shadow-xl">
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 p-4">
          <div>
            <h3 className="text-base font-semibold text-slate-950">Tratar solicitacao LGPD</h3>
            <p className="mt-1 text-sm text-slate-500">
              Atualize o status ou execute a anonimizacao quando o pedido for de exclusao.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setRequestModalOpen(false)}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-3 overflow-y-auto p-4">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-semibold text-slate-950">
                {REQUEST_TYPE_LABEL[requestToProcess.request_type] || requestToProcess.request_type}
              </div>
              <CopyableCode label="ID" value={requestToProcess.id} />
            </div>
            <div className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
              <span>Criada: {formatDate(requestToProcess.created_at)}</span>
              <span>Prazo: {formatDate(requestToProcess.due_at)}</span>
              <span>Solicitante: {requestToProcess.requester_name || "-"}</span>
              <span>Email: {requestToProcess.requester_email || "-"}</span>
            </div>
          </div>

          {requestToProcess.request_type === "deletion" &&
          requestToProcess.subject_type === "customer" ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
                <div className="min-w-0 text-sm">
                  <div className="font-semibold text-red-900">
                    Exclusao LGPD: proximo passo e anonimizar
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-red-700">
                    Remove dados pessoais do titular e dos pets, revoga consentimentos e preserva
                    historico financeiro/vendas sem identificadores.
                  </p>
                </div>
              </div>
              <ActionButton
                icon={Trash2}
                intent="delete"
                tone="soft"
                onClick={abrirDialogAnonimizacao}
                disabled={!canAnonymizeSelected}
                className="mt-3 w-full"
              >
                Anonimizar titular
              </ActionButton>
            </div>
          ) : null}

          <label className="block text-sm font-medium text-slate-700">
            Status
            <select
              value={processForm.status}
              onChange={(event) =>
                setProcessForm((current) => ({
                  ...current,
                  status: event.target.value,
                }))
              }
              className="mt-1 h-9 w-full rounded-lg border border-slate-300 px-3 text-sm"
            >
              {REQUEST_STATUS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm font-medium text-slate-700">
            Observacao / resposta
            <textarea
              value={processForm.resolution_notes}
              onChange={(event) =>
                setProcessForm((current) => ({
                  ...current,
                  resolution_notes: event.target.value,
                }))
              }
              rows={4}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Registre o que foi feito, resposta enviada ou motivo da rejeicao..."
            />
          </label>
        </div>
        <div className="flex flex-col-reverse gap-2 border-t border-slate-200 p-4 sm:flex-row sm:justify-end">
          <ActionButton
            intent="neutral"
            tone="soft"
            onClick={() => setRequestModalOpen(false)}
            disabled={saving}
          >
            Fechar
          </ActionButton>
          <ActionButton icon={Save} intent="edit" onClick={processarSolicitacao} loading={saving}>
            Salvar processamento
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
