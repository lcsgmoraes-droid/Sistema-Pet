import CustomerIdentity from "../../../components/ui/CustomerIdentity";
import StatusBadge from "../../../components/ui/StatusBadge";
import PetAvatar from "../../../components/ui/PetAvatar";
import { formatCurrency } from "../banhoTosaUtils";

const SLOT_MINUTOS = 30;

export default function BanhoTosaSugestoesSlots({
  agendamentos = [],
  capacidade,
  dataRef,
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
        <p className="mb-3 text-sm font-semibold text-slate-900">
          Compromissos do dia selecionado
        </p>
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
        !selected && neutro
          ? "border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
          : "",
      ]
        .filter(Boolean)
        .join(" ")}
      title={slot.descricao}
    >
      <div>{slot.horario}</div>
      <div className="mt-0.5 text-[10px] opacity-80">
        {slot.livre
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
              {inicio || "--:--"}{fim ? ` - ${fim}` : ""}
            </span>
            <StatusBadge status={agendamento.status} />
          </div>
          <div className="mt-1 truncate text-sm font-medium text-slate-700">
            {agendamento.pet_nome || `Pet #${agendamento.pet_id}`}
          </div>
          <CustomerIdentity
            className="mt-0.5 text-xs text-slate-500"
            codeLabel="Cod. tutor"
            fallback={`Tutor #${agendamento.cliente_id || "-"}`}
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

function montarSlotsModal({ agendamentos, capacidade, form, recursos, sugestoes }) {
  const inicio = minutos(capacidade?.janela_inicio || "08:00");
  const fim = minutos(capacidade?.janela_fim || "18:00");
  const recursosAtivos = recursos.filter((recurso) => recurso.ativo);
  const recursoSelecionadoId = form.recurso_id ? String(form.recurso_id) : "";
  const recursosDoSlot = recursoSelecionadoId
    ? recursosAtivos.filter((recurso) => String(recurso.id) === recursoSelecionadoId)
    : recursosAtivos;
  const slots = [];

  for (let cursor = inicio; cursor < fim; cursor += SLOT_MINUTOS) {
    const horario = labelHora(cursor);
    const sugestoesSlot = sugestoes.filter((slot) => hora(slot.horario_inicio) === horario);
    const sugestao = sugestoesSlot[0] || null;
    const ocupados = agendamentos.filter((agendamento) => {
      if (recursoSelecionadoId && String(agendamento.recurso_id || "") !== recursoSelecionadoId) {
        return false;
      }
      return sobrepoeSlot(agendamento, cursor, cursor + SLOT_MINUTOS);
    });
    const livre =
      Boolean(sugestao) ||
      temCapacidadeLivre(recursosDoSlot, agendamentos, cursor, cursor + SLOT_MINUTOS) ||
      (!recursosAtivos.length && ocupados.length === 0);

    slots.push({
      descricao: descreverSlot({ livre, ocupados, sugestao }),
      horario,
      livre,
      ocupados,
      sugestao,
    });
  }

  return slots;
}

function temCapacidadeLivre(recursos, agendamentos, inicioSlot, fimSlot) {
  return recursos.some((recurso) => {
    const capacidade = Math.max(Number(recurso.capacidade_simultanea || recurso.capacidade || 1), 1);
    const ocupacao = agendamentos.filter((agendamento) => {
      if (String(agendamento.recurso_id || "") !== String(recurso.id)) return false;
      return sobrepoeSlot(agendamento, inicioSlot, fimSlot);
    }).length;
    return ocupacao < capacidade;
  });
}

function descreverSlot({ livre, ocupados, sugestao }) {
  if (livre && sugestao?.recurso_nome) return `Livre em ${sugestao.recurso_nome}`;
  if (livre) return "Horario livre";
  if (ocupados.length) return ocupados.map((item) => item.pet_nome || `Pet #${item.pet_id}`).join(", ");
  return "Sem vaga sugerida para este horario";
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

function sobrepoeSlot(agendamento, inicioSlot, fimSlot) {
  const inicio = minutos(hora(agendamento.data_hora_inicio));
  const fim = minutos(hora(agendamento.data_hora_fim_prevista)) || inicio;
  return inicio < fimSlot && fim > inicioSlot;
}

function hora(valor) {
  return String(valor || "").slice(11, 16);
}

function minutos(valor) {
  const [horaValor, minutoValor] = String(valor || "00:00").split(":");
  return Number(horaValor || 0) * 60 + Number(minutoValor || 0);
}

function labelHora(totalMinutos) {
  const horaValor = Math.floor(totalMinutos / 60);
  const minutoValor = totalMinutos % 60;
  return `${String(horaValor).padStart(2, "0")}:${String(minutoValor).padStart(2, "0")}`;
}
