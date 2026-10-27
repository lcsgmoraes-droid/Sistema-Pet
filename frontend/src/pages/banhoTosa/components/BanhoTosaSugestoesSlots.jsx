import CustomerIdentity from "../../../components/ui/CustomerIdentity";
import StatusBadge from "../../../components/ui/StatusBadge";
import PetAvatar from "../../../components/ui/PetAvatar";
import PetIdentity from "../../../components/ui/PetIdentity";
import { formatCurrency } from "../banhoTosaUtils";
import { montarSlotsModal } from "./banhoTosaSlotsModal";

export default function BanhoTosaSugestoesSlots({
  agendamentos = [],
  capacidade,
  dataRef,
  duracaoMinutos,
  form,
  loadingAgenda,
  loadingSugestoes,
  recursos = [],
  sugestoes = [],
  onChangeField,
  onUseSlot,
}) {
  const slots = montarSlotsModal({
    agendamentos,
    capacidade,
    dataRef,
    duracaoMinutos,
    form,
    recursos,
    sugestoes,
  });

  function selecionarSlot(slot) {
    if (slot.sugestao) {
      onUseSlot(slot.sugestao);
      return;
    }
    onChangeField("hora", slot.horario);
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-900">Agenda do dia</p>
            <p className="text-xs text-slate-500">{formatarData(dataRef)}</p>
          </div>
          <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600">
            {agendamentos.length} agendamento(s)
          </span>
        </div>

        <div className="mt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Horarios livres e ocupados
          </p>
          {loadingSugestoes ? (
            <p className="rounded-lg bg-white p-4 text-sm font-medium text-slate-500">
              Procurando horarios...
            </p>
          ) : (
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
              {slots.map((slot) => (
                <HorarioButton
                  key={slot.horario}
                  selected={form.hora === slot.horario}
                  slot={slot}
                  onSelect={selecionarSlot}
                />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <p className="mb-3 text-sm font-semibold text-slate-900">Compromissos do dia selecionado</p>
        {loadingAgenda ? (
          <div className="text-sm text-slate-500">Carregando agenda do dia...</div>
        ) : agendamentos.length === 0 ? (
          <div className="rounded-lg border border-dashed border-emerald-200 bg-emerald-50 px-3 py-4 text-sm text-emerald-700">
            Nenhum compromisso neste dia. A agenda esta livre.
          </div>
        ) : (
          <div className="max-h-[300px] space-y-2 overflow-y-auto pr-1">
            {agendamentos.map((agendamento) => (
              <CompromissoCard key={agendamento.id} agendamento={agendamento} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function HorarioButton({ selected, slot, onSelect }) {
  const ocupado = slot.ocupados.length > 0 && !slot.livre;
  const neutro = !slot.livre && slot.ocupados.length === 0;

  return (
    <button
      type="button"
      onClick={() => onSelect(slot)}
      className={[
        "rounded-lg border px-2 py-2 text-xs font-medium transition-colors",
        selected && slot.livre ? "border-blue-600 bg-blue-600 text-white" : "",
        selected && !slot.livre ? "border-amber-500 bg-amber-500 text-white" : "",
        !selected && slot.livre
          ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
          : "",
        !selected && ocupado
          ? "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
          : "",
        !selected && neutro ? "border-slate-200 bg-white text-slate-500 hover:bg-slate-50" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      title={slot.descricao}
    >
      <div>{slot.horario}</div>
      <div className="mt-0.5 text-[10px] opacity-80">
        {slot.foraExpediente
          ? "Fora expediente"
          : slot.livre
            ? slot.ocupados.length
              ? `Livre + ${slot.ocupados.length} ocup.`
              : "Livre"
            : slot.ocupados.length
              ? `${slot.ocupados.length} ocupado(s)`
              : "Sem vaga"}
      </div>
    </button>
  );
}

function CompromissoCard({ agendamento }) {
  const inicio = hora(agendamento.data_hora_inicio);
  const fim = hora(agendamento.data_hora_fim_prevista);
  const servico = agendamento.servicos?.[0]?.nome_servico_snapshot || "Banho & Tosa";

  return (
    <article className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="flex gap-3">
        <PetAvatar
          alt={agendamento.pet_nome || "Pet"}
          name={agendamento.pet_nome}
          size="sm"
          url={agendamento.pet_foto_url}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-slate-900">
              {inicio || "--:--"}
              {fim ? ` - ${fim}` : ""}
            </span>
            <StatusBadge status={agendamento.status} />
          </div>
          <PetIdentity
            className="mt-1 text-sm"
            fallback={`Pet #${agendamento.pet_id || "-"}`}
            layout="inline"
            nameClassName="font-medium text-slate-700"
            record={agendamento}
          />
          <CustomerIdentity
            className="mt-0.5 text-xs text-slate-500"
            codeLabel="Cod. tutor"
            fallback={"Tutor não informado"}
            label="Tutor"
            nameClassName="font-medium text-slate-500"
            record={agendamento}
            showLabel
          />
          <div className="truncate text-xs text-slate-500">
            {[servico, agendamento.recurso_nome].filter(Boolean).join(" - ")}
          </div>
          <div className="mt-1 text-xs font-semibold text-emerald-700">
            {formatCurrency(agendamento.valor_previsto)}
          </div>
        </div>
      </div>
    </article>
  );
}

function formatarData(dataRef) {
  if (!dataRef) return "Selecione uma data";
  return new Date(`${dataRef}T12:00:00`).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    weekday: "long",
    year: "numeric",
  });
}

function hora(valor) {
  return String(valor || "").slice(11, 16);
}
