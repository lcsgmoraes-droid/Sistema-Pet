import { CheckCircle2, XCircle } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import CustomerIdentity from "../../../components/ui/CustomerIdentity";
import PetAvatar from "../../../components/ui/PetAvatar";
import PetIdentity from "../../../components/ui/PetIdentity";
import StatusBadge from "../../../components/ui/StatusBadge";
import { formatCurrency } from "../banhoTosaUtils";
import BanhoTosaVetAlertas from "./BanhoTosaVetAlertas";

export default function BanhoTosaAgendaCard({ agendamento, onCancelar, onCheckIn }) {
  const hora = String(agendamento.data_hora_inicio || "").slice(11, 16);
  const podeCheckIn = !["cancelado", "entregue", "no_show", "em_atendimento"].includes(
    agendamento.status,
  );

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 gap-3">
          <PetAvatar
            alt={agendamento.pet_nome || "Pet"}
            name={agendamento.pet_nome}
            url={agendamento.pet_foto_url}
          />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">
              {hora} -{" "}
              <PetIdentity
                className="align-middle"
                fallback={`Pet #${agendamento.pet_id || "-"}`}
                layout="inline"
                nameClassName="font-semibold text-slate-900"
                record={agendamento}
              />
            </p>
            <CustomerIdentity
              className="mt-0.5 text-xs text-slate-500"
              codeLabel="Cod. tutor"
              fallback={`Tutor #${agendamento.cliente_id || "-"}`}
              nameClassName="font-medium text-slate-500"
              record={agendamento}
              showLabel
              label="Tutor"
            />
            <p className="mt-1 text-sm font-medium text-slate-700">
              {agendamento.servicos?.[0]?.nome_servico_snapshot || "Banho & Tosa"} -{" "}
              {formatCurrency(agendamento.valor_previsto)}
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
        </div>
        <StatusBadge status={agendamento.status} />
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {podeCheckIn && (
          <ActionButton
            icon={CheckCircle2}
            intent="create"
            onClick={() => onCheckIn(agendamento)}
            size="xs"
          >
            Fazer check-in
          </ActionButton>
        )}
        {!["cancelado", "entregue", "no_show"].includes(agendamento.status) && (
          <ActionButton
            icon={XCircle}
            intent="delete"
            onClick={() => onCancelar(agendamento)}
            size="xs"
            tone="soft"
          >
            Cancelar
          </ActionButton>
        )}
      </div>
    </div>
  );
}
