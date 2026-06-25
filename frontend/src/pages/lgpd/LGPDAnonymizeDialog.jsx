import { Trash2, X } from "lucide-react";
import ActionButton from "../../components/ui/ActionButton";

export default function LGPDAnonymizeDialog({
  anonymizeDialogOpen,
  anonymizeForm,
  confirmarAnonimizacao,
  saving,
  setAnonymizeDialogOpen,
  setAnonymizeForm,
}) {
  if (!anonymizeDialogOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 p-4">
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-red-100 p-2 text-red-600">
              <Trash2 className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-950">
                Anonimizar dados do titular
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                Essa acao remove identificadores pessoais e conclui a solicitacao LGPD.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setAnonymizeDialogOpen(false)}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-4 p-4">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            O codigo interno, vendas, pagamentos e historico operacional continuam preservados para
            auditoria. Nome, documentos, contatos, enderecos, observacoes sensiveis, dados dos pets
            e consentimentos ativos serao removidos.
          </div>
          <label className="block text-sm font-medium text-slate-700">
            Observacao da conclusao
            <textarea
              value={anonymizeForm.resolution_notes}
              onChange={(event) =>
                setAnonymizeForm((current) => ({
                  ...current,
                  resolution_notes: event.target.value,
                }))
              }
              rows={3}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Ex.: Solicitacao validada com o titular e anonimizada no ERP."
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Digite ANONIMIZAR para confirmar
            <input
              value={anonymizeForm.confirmacao}
              onChange={(event) =>
                setAnonymizeForm((current) => ({
                  ...current,
                  confirmacao: event.target.value,
                }))
              }
              className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
              placeholder="ANONIMIZAR"
            />
          </label>
        </div>
        <div className="flex flex-col-reverse gap-2 border-t border-slate-200 p-4 sm:flex-row sm:justify-end">
          <ActionButton
            intent="neutral"
            tone="soft"
            onClick={() => setAnonymizeDialogOpen(false)}
            disabled={saving}
          >
            Cancelar
          </ActionButton>
          <ActionButton
            icon={Trash2}
            intent="delete"
            onClick={confirmarAnonimizacao}
            loading={saving}
            disabled={anonymizeForm.confirmacao.trim().toUpperCase() !== "ANONIMIZAR"}
          >
            Confirmar anonimizacao
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
