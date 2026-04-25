import { X } from "lucide-react";
import { STATUS_BADGE, STATUS_LABEL, TIPO_BADGE, TIPO_LABEL } from "./agendaUtils";

export default function GerenciarAgendamentoModal({
  agendamento,
  tipoAgendamento,
  mensagem,
  podeVoltarStatus,
  labelVoltarStatus,
  podeExcluir,
  labelAbrir,
  abrindoAgendamentoId,
  processandoAgendamentoId,
  onClose,
  onEdit,
  onVoltarStatus,
  onExcluir,
  onIniciar,
}) {
  if (!agendamento) return null;

  const processando = processandoAgendamentoId === agendamento.id;
  const abrindo = abrindoAgendamentoId === agendamento.id;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-bold text-gray-800">Gerenciar agendamento</h2>
            <p className="mt-1 text-sm text-gray-500">{mensagem}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar modal"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-5 grid gap-4 rounded-xl border border-gray-200 bg-gray-50 p-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Horario</p>
            <p className="mt-1 text-sm font-semibold text-gray-800">
              {new Date(agendamento.data_hora).toLocaleDateString("pt-BR", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
              })}{" "}
              as {String(agendamento.data_hora || "").slice(11, 16)}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Status</p>
            <span
              className={`mt-1 inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                STATUS_BADGE[agendamento.status] ?? "bg-gray-100 text-gray-600"
              }`}
            >
              {STATUS_LABEL[agendamento.status] ?? agendamento.status}
            </span>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Tutor</p>
            <p className="mt-1 text-sm text-gray-800">{agendamento.cliente_nome || "-"}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Pet</p>
            <p className="mt-1 text-sm text-gray-800">{agendamento.pet_nome || "-"}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Veterinario</p>
            <p className="mt-1 text-sm text-gray-800">{agendamento.veterinario_nome || "Nao definido"}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Consultorio</p>
            <p className="mt-1 text-sm text-gray-800">{agendamento.consultorio_nome || "Nao definido"}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Tipo</p>
            <span
              className={`mt-1 inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                TIPO_BADGE[tipoAgendamento] ?? "bg-gray-100 text-gray-600"
              }`}
            >
              {TIPO_LABEL[tipoAgendamento] ?? "Consulta"}
            </span>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Motivo</p>
            <p className="mt-1 text-sm text-gray-800">{agendamento.motivo || "Sem motivo informado"}</p>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onEdit}
            disabled={processando}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          >
            Editar agendamento
          </button>
          {podeVoltarStatus && (
            <button
              type="button"
              onClick={onVoltarStatus}
              disabled={processando}
              className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-700 hover:bg-amber-100 disabled:opacity-60"
            >
              {labelVoltarStatus}
            </button>
          )}
          {podeExcluir && (
            <button
              type="button"
              onClick={onExcluir}
              disabled={processando}
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100 disabled:opacity-60"
            >
              Excluir agendamento
            </button>
          )}
        </div>

        {!podeExcluir && !podeVoltarStatus && agendamento.consulta_id && (
          <p className="mt-3 text-xs text-gray-500">
            Este agendamento ja possui atendimento vinculado. Se foi apenas um teste, use "Desfazer inicio do atendimento". Se ja houver dados clinicos, trate primeiro o atendimento.
          </p>
        )}

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
          >
            Fechar
          </button>
          <button
            type="button"
            onClick={onIniciar}
            disabled={abrindo || processando}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {abrindo ? "Abrindo..." : labelAbrir}
          </button>
        </div>
      </div>
    </div>
  );
}
