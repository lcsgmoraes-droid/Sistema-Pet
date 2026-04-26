import { Activity } from "lucide-react";

import {
  STATUS_BADGE,
  STATUS_COLOR,
  STATUS_LABEL,
  TIPO_ACAO,
  TIPO_BADGE,
  TIPO_LABEL,
  normalizarTipoAgendamento,
} from "./agendaUtils";

export default function NovoAgendamentoAgendaDiaSection({
  abrindoAgendamentoId,
  agendaDiaModal,
  carregandoAgendaDiaModal,
  formNovo,
  horariosAgendaModal,
  onChangeCampo,
  onOpenAgendamento,
}) {
  return (
    <div className="space-y-4">
      <HorariosSugeridos
        agendaDiaModal={agendaDiaModal}
        formNovo={formNovo}
        horariosAgendaModal={horariosAgendaModal}
        onChangeCampo={onChangeCampo}
      />

      <CompromissosDia
        abrindoAgendamentoId={abrindoAgendamentoId}
        agendaDiaModal={agendaDiaModal}
        carregandoAgendaDiaModal={carregandoAgendaDiaModal}
        onOpenAgendamento={onOpenAgendamento}
      />
    </div>
  );
}

function HorariosSugeridos({ agendaDiaModal, formNovo, horariosAgendaModal, onChangeCampo }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-800">Agenda do dia</p>
          <p className="text-xs text-gray-500">
            {formNovo.data
              ? new Date(`${formNovo.data}T12:00:00`).toLocaleDateString("pt-BR", {
                  weekday: "long",
                  day: "2-digit",
                  month: "long",
                  year: "numeric",
                })
              : "Selecione uma data"}
          </p>
        </div>
        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-gray-600">
          {agendaDiaModal.length} agendamento(s)
        </span>
      </div>

      <div className="mt-4">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
          Horarios sugeridos
        </p>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {horariosAgendaModal.map((slot) => (
            <button
              key={slot.horario}
              type="button"
              onClick={() => onChangeCampo("hora", slot.horario)}
              className={`rounded-lg border px-2 py-2 text-xs font-medium transition-colors ${
                formNovo.hora === slot.horario
                  ? slot.livre
                    ? "border-blue-600 bg-blue-600 text-white"
                    : "border-amber-500 bg-amber-500 text-white"
                  : slot.livre
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                  : "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
              }`}
            >
              <div>{slot.horario}</div>
              <div className="mt-0.5 text-[10px] opacity-80">
                {slot.livre ? "Livre" : `${slot.ocupados.length} ocupado(s)`}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function CompromissosDia({
  abrindoAgendamentoId,
  agendaDiaModal,
  carregandoAgendaDiaModal,
  onOpenAgendamento,
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="mb-3 text-sm font-semibold text-gray-800">Compromissos do dia selecionado</p>
      {carregandoAgendaDiaModal ? (
        <div className="text-sm text-gray-500">Carregando agenda do dia...</div>
      ) : agendaDiaModal.length === 0 ? (
        <div className="rounded-lg border border-dashed border-emerald-200 bg-emerald-50 px-3 py-4 text-sm text-emerald-700">
          Nenhum compromisso neste dia. A agenda esta livre.
        </div>
      ) : (
        <div className="max-h-[300px] space-y-2 overflow-y-auto pr-1">
          {agendaDiaModal.map((agendamento) => (
            <AgendamentoDiaCard
              key={agendamento.id}
              abrindoAgendamentoId={abrindoAgendamentoId}
              agendamento={agendamento}
              onOpenAgendamento={onOpenAgendamento}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function AgendamentoDiaCard({ abrindoAgendamentoId, agendamento, onOpenAgendamento }) {
  const tipoAgendamento = normalizarTipoAgendamento(agendamento.tipo);

  return (
    <button
      type="button"
      onClick={() => onOpenAgendamento(agendamento)}
      className={`w-full rounded-lg border px-3 py-2 text-left ${
        STATUS_COLOR[agendamento.status] ?? "border-l-gray-200 bg-white"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-gray-800">
          {String(agendamento.data_hora || "").slice(11, 16) || "--:--"}
        </span>
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
            STATUS_BADGE[agendamento.status] ?? "bg-gray-100 text-gray-600"
          }`}
        >
          {STATUS_LABEL[agendamento.status] ?? agendamento.status}
        </span>
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
            TIPO_BADGE[tipoAgendamento] ?? "bg-gray-100 text-gray-600"
          }`}
        >
          {TIPO_LABEL[tipoAgendamento] ?? "Consulta"}
        </span>
        {agendamento.is_emergencia && <Activity size={12} className="ml-auto text-red-500" />}
      </div>
      <div className="mt-1 text-sm font-medium text-gray-700">
        {agendamento.pet_nome ?? `Pet #${String(agendamento.pet_id ?? "").slice(0, 6)}`}
      </div>
      <div className="text-[11px] text-gray-500">
        {[agendamento.veterinario_nome, agendamento.consultorio_nome].filter(Boolean).join(" - ") ||
          "Sem profissional/sala"}
      </div>
      <div className="text-xs text-gray-500">{agendamento.motivo ?? "Sem motivo informado"}</div>
      <div className="mt-2 text-[11px] font-medium text-blue-600">
        {abrindoAgendamentoId === agendamento.id
          ? "Abrindo fluxo..."
          : TIPO_ACAO[tipoAgendamento] ?? "Abrir atendimento"}
      </div>
    </button>
  );
}
