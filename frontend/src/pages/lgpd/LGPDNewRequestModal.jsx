import { FileText, X } from "lucide-react";
import ActionButton from "../../components/ui/ActionButton";
import CustomerIdentity from "../../components/ui/CustomerIdentity";
import { REQUEST_TYPES } from "./lgpdConstants";

export default function LGPDNewRequestModal({
  criarSolicitacao,
  newRequest,
  newRequestModalOpen,
  saving,
  selectedClienteId,
  selectedCustomer,
  setNewRequest,
  setNewRequestModalOpen,
}) {
  if (!newRequestModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl">
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 p-4">
          <div>
            <h3 className="text-base font-semibold text-slate-950">Registrar pedido LGPD</h3>
            <p className="mt-1 text-sm text-slate-500">
              Use quando o titular pediu acesso, exportacao, correcao, exclusao ou revogacao por
              telefone, loja ou atendimento.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setNewRequestModalOpen(false)}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="grid gap-3 p-4">
          {selectedCustomer ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <CustomerIdentity customer={selectedCustomer} />
            </div>
          ) : null}
          <select
            value={newRequest.request_type}
            onChange={(event) =>
              setNewRequest((current) => ({
                ...current,
                request_type: event.target.value,
              }))
            }
            className="h-9 rounded-lg border border-slate-300 px-3 text-sm"
          >
            {REQUEST_TYPES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              value={newRequest.requester_name}
              onChange={(event) =>
                setNewRequest((current) => ({
                  ...current,
                  requester_name: event.target.value,
                }))
              }
              className="h-9 rounded-lg border border-slate-300 px-3 text-sm"
              placeholder="Nome do solicitante"
            />
            <input
              value={newRequest.requester_email}
              onChange={(event) =>
                setNewRequest((current) => ({
                  ...current,
                  requester_email: event.target.value,
                }))
              }
              className="h-9 rounded-lg border border-slate-300 px-3 text-sm"
              placeholder="Email"
            />
          </div>
          <input
            value={newRequest.requester_phone}
            onChange={(event) =>
              setNewRequest((current) => ({
                ...current,
                requester_phone: event.target.value,
              }))
            }
            className="h-9 rounded-lg border border-slate-300 px-3 text-sm"
            placeholder="Telefone"
          />
          <textarea
            value={newRequest.details}
            onChange={(event) =>
              setNewRequest((current) => ({
                ...current,
                details: event.target.value,
              }))
            }
            rows={3}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Detalhes do pedido do titular..."
          />
        </div>
        <div className="flex flex-col-reverse gap-2 border-t border-slate-200 p-4 sm:flex-row sm:justify-end">
          <ActionButton
            intent="neutral"
            tone="soft"
            onClick={() => setNewRequestModalOpen(false)}
            disabled={saving}
          >
            Cancelar
          </ActionButton>
          <ActionButton
            icon={FileText}
            intent="create"
            onClick={criarSolicitacao}
            loading={saving}
            disabled={!selectedClienteId}
          >
            Registrar para o titular selecionado
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
