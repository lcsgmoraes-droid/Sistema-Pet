import { ArrowUp, CheckCircle2, FileText, Pencil } from "lucide-react";

import ConsultaModalShell from "./ConsultaModalShell";
import { listarAcoesRascunhoSalvo, RASCUNHO_SALVO_ACOES } from "./consultaRascunhoFeedback";

const iconesPorAcao = {
  [RASCUNHO_SALVO_ACOES.CONTINUAR]: Pencil,
  [RASCUNHO_SALVO_ACOES.TOPO]: ArrowUp,
  [RASCUNHO_SALVO_ACOES.LISTA]: FileText,
};

export default function ConsultaRascunhoSalvoModal({
  isOpen,
  mensagem,
  onContinuar,
  onIrParaTopo,
  onSairParaLista,
}) {
  const handlers = {
    [RASCUNHO_SALVO_ACOES.CONTINUAR]: onContinuar,
    [RASCUNHO_SALVO_ACOES.TOPO]: onIrParaTopo,
    [RASCUNHO_SALVO_ACOES.LISTA]: onSairParaLista,
  };

  return (
    <ConsultaModalShell
      isOpen={isOpen}
      title="Consulta salva"
      subtitle="O rascunho foi gravado e voce pode escolher o proximo passo."
      onClose={onContinuar}
      closeAriaLabel="Fechar aviso de rascunho salvo"
      maxWidthClass="max-w-lg"
    >
      <div className="mt-5 rounded-xl border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-800">
        <div className="flex items-start gap-3">
          <CheckCircle2 size={20} className="mt-0.5 shrink-0" />
          <p>{mensagem || "Rascunho salvo com sucesso."}</p>
        </div>
      </div>

      <div className="mt-6 grid gap-2 sm:grid-cols-3">
        {listarAcoesRascunhoSalvo().map((acao) => {
          const Icone = iconesPorAcao[acao.id];
          const isPrincipal = acao.id === RASCUNHO_SALVO_ACOES.CONTINUAR;

          return (
            <button
              key={acao.id}
              type="button"
              onClick={handlers[acao.id]}
              className={
                isPrincipal
                  ? "inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  : "inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              }
            >
              <Icone size={16} />
              {acao.label}
            </button>
          );
        })}
      </div>
    </ConsultaModalShell>
  );
}
