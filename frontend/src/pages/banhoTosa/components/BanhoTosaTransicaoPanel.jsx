import { useEffect, useState } from "react";
import { Clock3, Play, X } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import { SelectField, TextField } from "../../../components/ui/FormField";

const ETAPAS_OPERACIONAIS = new Set(["banho", "secagem", "tosa", "higiene", "preparo"]);

export default function BanhoTosaTransicaoPanel({
  atendimento,
  etapa,
  funcionarios = [],
  processing = false,
  recursos = [],
  onClose,
  onConfirm,
}) {
  const [responsavelId, setResponsavelId] = useState("");
  const [recursoId, setRecursoId] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const operacional = ETAPAS_OPERACIONAIS.has(etapa);

  useEffect(() => {
    const etapaAtual = (atendimento?.etapas || []).find((item) => item.inicio_em && !item.fim_em);
    setResponsavelId(String(etapaAtual?.responsavel_id || ""));
    setRecursoId(String(etapaAtual?.recurso_id || ""));
    setObservacoes("");
  }, [atendimento?.id, etapa]);

  if (!atendimento || !etapa) return null;

  function confirmar(event) {
    event.preventDefault();
    onConfirm({
      tipo: etapa,
      iniciar_timer: operacional,
      responsavel_id: responsavelId ? Number(responsavelId) : null,
      recurso_id: recursoId ? Number(recursoId) : null,
      observacoes: observacoes.trim() || null,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 backdrop-blur-[1px] sm:items-center sm:p-4">
      <form
        aria-label={`Mover ${atendimento.pet_nome || "pet"} para ${labelEtapa(etapa)}`}
        aria-modal="true"
        className="w-full max-w-lg rounded-t-2xl border border-slate-200 bg-white p-5 shadow-2xl sm:rounded-2xl"
        role="dialog"
        onSubmit={confirmar}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
              Próxima etapa
            </p>
            <h2 className="mt-1 text-lg font-semibold text-slate-950">
              {atendimento.pet_nome || `Pet #${atendimento.pet_id}`} → {labelEtapa(etapa)}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {operacional
                ? "O contador começa assim que você confirmar."
                : "A etapa atual será encerrada ao confirmar."}
            </p>
          </div>
          <button
            aria-label="Fechar"
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            type="button"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>

        {operacional && (
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <SelectField label="Responsável" value={responsavelId} onChange={setResponsavelId}>
              <option value="">Sem responsável definido</option>
              {funcionarios.map((funcionario) => (
                <option key={funcionario.id} value={funcionario.id}>
                  {funcionario.nome || `Funcionário #${funcionario.id}`}
                </option>
              ))}
            </SelectField>
            <SelectField label="Recurso / box" value={recursoId} onChange={setRecursoId}>
              <option value="">Sem recurso definido</option>
              {recursos
                .filter((recurso) => recurso.ativo !== false)
                .map((recurso) => (
                  <option key={recurso.id} value={recurso.id}>
                    {recurso.nome}
                  </option>
                ))}
            </SelectField>
          </div>
        )}

        <TextField
          className="mt-4"
          label="Observação da etapa"
          placeholder="Ex.: usar shampoo hipoalergênico"
          value={observacoes}
          onChange={setObservacoes}
        />

        {operacional && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-sm text-blue-800">
            <Clock3 size={17} className="shrink-0" />O tempo previsto será calculado pelo porte e
            pela pelagem do pet.
          </div>
        )}

        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <ActionButton
            className="justify-center"
            intent="neutral"
            tone="soft"
            type="button"
            onClick={onClose}
          >
            Voltar
          </ActionButton>
          <ActionButton
            className="justify-center"
            icon={operacional ? Play : undefined}
            intent="create"
            loading={processing}
            size="md"
            type="submit"
          >
            {operacional ? `Iniciar ${labelEtapa(etapa)}` : `Mover para ${labelEtapa(etapa)}`}
          </ActionButton>
        </div>
      </form>
    </div>
  );
}

function labelEtapa(etapa) {
  return (
    {
      chegou: "Chegou",
      banho: "Banho",
      secagem: "Secagem",
      tosa: "Tosa",
      higiene: "Higiene",
      preparo: "Preparo",
      pronto: "Pronto",
      entregue: "Entregue",
    }[etapa] || etapa
  );
}
