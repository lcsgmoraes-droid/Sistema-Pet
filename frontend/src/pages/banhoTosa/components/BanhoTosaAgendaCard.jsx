import { formatCurrency } from "../banhoTosaUtils";
import BanhoTosaVetAlertas from "./BanhoTosaVetAlertas";

export default function BanhoTosaAgendaCard({ agendamento, onCancelar, onCheckIn }) {
  const hora = String(agendamento.data_hora_inicio || "").slice(11, 16);
  const podeCheckIn = !["cancelado", "entregue", "no_show", "em_atendimento"].includes(
    agendamento.status,
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-lg font-black text-slate-900">
            {hora} - {agendamento.pet_nome || `Pet #${agendamento.pet_id}`}
          </p>
          <p className="text-sm text-slate-500">
            Tutor: {agendamento.cliente_nome || `#${agendamento.cliente_id}`}
          </p>
          <p className="mt-1 text-sm font-semibold text-slate-700">
            {agendamento.servicos?.[0]?.nome_servico_snapshot || "Banho & Tosa"} - {formatCurrency(agendamento.valor_previsto)}
          </p>
          <p className="mt-1 text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
            {agendamento.recurso_nome
              ? `${agendamento.recurso_nome} (${agendamento.recurso_tipo || "recurso"})`
              : "Sem recurso definido"}
          </p>
          <BanhoTosaVetAlertas
            compact
            perfil={agendamento.perfil_comportamental_snapshot}
            restricoes={agendamento.restricoes_veterinarias_snapshot}
          />
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-bold uppercase tracking-[0.12em] text-slate-600">
          {agendamento.status}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {podeCheckIn && (
          <button
            type="button"
            onClick={() => onCheckIn(agendamento)}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-emerald-600"
          >
            Fazer check-in
          </button>
        )}
        {!["cancelado", "entregue", "no_show"].includes(agendamento.status) && (
          <button
            type="button"
            onClick={() => onCancelar(agendamento)}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-600 transition hover:border-red-200 hover:text-red-600"
          >
            Cancelar
          </button>
        )}
      </div>
    </div>
  );
}
