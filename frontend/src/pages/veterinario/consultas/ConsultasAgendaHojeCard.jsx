import { AlertCircle, CalendarClock, PlayCircle, RefreshCw } from "lucide-react";

import PetIdentity from "../../../components/ui/PetIdentity";
import { getAgendamentoConsultaActionLabel } from "../fluxoConsultaAgendamentoUtils";
import { STATUS_BADGE, STATUS_LABEL, TIPO_BADGE, TIPO_LABEL, normalizarTipoAgendamento } from "../agenda/agendaUtils";

export default function ConsultasAgendaHojeCard({
  abrindoAgendamentoId,
  agendamentos,
  carregando,
  erro,
  erroAcao,
  onAbrirAgenda,
  onIniciarAgendamento,
  onRecarregar,
}) {
  return (
    <section className="rounded-xl border border-blue-100 bg-blue-50/60 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <CalendarClock size={17} className="text-blue-600" />
            Agendamentos de hoje
          </h2>
          <p className="mt-1 text-xs text-slate-500">Pacientes agendados para atendimento clinico nesta data.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onRecarregar}
            className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-white px-3 py-2 text-xs font-medium text-blue-700 hover:bg-blue-50"
          >
            <RefreshCw size={14} />
            Atualizar
          </button>
          <button
            type="button"
            onClick={onAbrirAgenda}
            className="rounded-lg border border-blue-200 bg-white px-3 py-2 text-xs font-medium text-blue-700 hover:bg-blue-50"
          >
            Ver agenda
          </button>
        </div>
      </div>

      {erro || erroAcao ? (
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          <AlertCircle size={14} />
          <span>{erro || erroAcao}</span>
        </div>
      ) : null}

      {carregando ? (
        <div className="mt-4 flex items-center justify-center py-6">
          <div className="h-6 w-6 animate-spin rounded-full border-b-2 border-blue-500" />
        </div>
      ) : agendamentos.length === 0 ? (
        <p className="mt-4 rounded-lg border border-dashed border-blue-200 bg-white px-4 py-5 text-center text-sm text-slate-500">
          Nenhum agendamento clinico aberto para hoje.
        </p>
      ) : (
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {agendamentos.map((agendamento) => (
            <AgendamentoHojeItem
              key={agendamento.id}
              abrindo={abrindoAgendamentoId === agendamento.id}
              agendamento={agendamento}
              onIniciarAgendamento={onIniciarAgendamento}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function AgendamentoHojeItem({ abrindo, agendamento, onIniciarAgendamento }) {
  const tipo = normalizarTipoAgendamento(agendamento.tipo);

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-slate-800">
          {String(agendamento.data_hora || "").slice(11, 16) || "--:--"}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${TIPO_BADGE[tipo] ?? "bg-gray-100 text-gray-600"}`}>
          {TIPO_LABEL[tipo] ?? "Consulta"}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_BADGE[agendamento.status] ?? "bg-gray-100 text-gray-600"}`}>
          {STATUS_LABEL[agendamento.status] ?? agendamento.status}
        </span>
      </div>

      <div className="mt-2 text-sm font-medium text-slate-800">
        <PetIdentity
          copyable={false}
          fallback={`Pet #${String(agendamento.pet_id ?? "").slice(0, 6) || "-"}`}
          layout="inline"
          nameClassName="font-medium text-slate-800"
          record={agendamento}
        />
      </div>
      <p className="mt-1 truncate text-xs text-slate-500">
        {[agendamento.veterinario_nome, agendamento.consultorio_nome].filter(Boolean).join(" - ") ||
          "Sem profissional/sala"}
      </p>
      <p className="mt-1 line-clamp-2 text-xs text-slate-500">
        {agendamento.motivo || "Sem motivo informado"}
      </p>

      <button
        type="button"
        onClick={() => onIniciarAgendamento(agendamento)}
        disabled={abrindo}
        className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
      >
        <PlayCircle size={14} />
        {abrindo ? "Abrindo..." : getAgendamentoConsultaActionLabel(agendamento)}
      </button>
    </article>
  );
}
