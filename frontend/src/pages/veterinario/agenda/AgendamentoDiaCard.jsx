import { Activity } from "lucide-react";
import PetIdentity from "../../../components/ui/PetIdentity";
import { getAgendamentoConsultaActionLabel } from "../fluxoConsultaAgendamentoUtils";

import {
  STATUS_BADGE,
  STATUS_COLOR,
  STATUS_LABEL,
  TIPO_ACAO,
  TIPO_BADGE,
  TIPO_CARD_COLOR,
  TIPO_LABEL,
  normalizarTipoAgendamento,
} from "./agendaUtils";

export default function AgendamentoDiaCard({ abrindoAgendamentoId, agendamento, onOpenAgendamento }) {
  const tipoAgendamento = normalizarTipoAgendamento(agendamento.tipo);

  return (
    <button
      type="button"
      onClick={() => onOpenAgendamento(agendamento)}
      className={`w-full rounded-lg border px-3 py-2 text-left ${
        TIPO_CARD_COLOR[tipoAgendamento] || STATUS_COLOR[agendamento.status] || "border-l-gray-200 bg-white"
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
        <PetIdentity
          copyable={false}
          fallback={`Pet #${String(agendamento.pet_id ?? "").slice(0, 6) || "-"}`}
          layout="inline"
          nameClassName="font-medium text-gray-700"
          record={agendamento}
        />
      </div>
      <div className="text-[11px] text-gray-500">
        {[agendamento.veterinario_nome, agendamento.consultorio_nome].filter(Boolean).join(" - ") ||
          "Sem profissional/sala"}
      </div>
      <div className="text-xs text-gray-500">{agendamento.motivo ?? "Sem motivo informado"}</div>
      <div className="mt-2 text-[11px] font-medium text-blue-600">
        {abrindoAgendamentoId === agendamento.id
          ? "Abrindo fluxo..."
          : tipoAgendamento === "consulta" || tipoAgendamento === "retorno"
            ? getAgendamentoConsultaActionLabel(agendamento)
            : TIPO_ACAO[tipoAgendamento] ?? "Abrir atendimento"}
      </div>
    </button>
  );
}
