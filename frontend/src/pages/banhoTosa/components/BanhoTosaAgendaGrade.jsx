const SLOT_MINUTOS = 30;

export default function BanhoTosaAgendaGrade({
  agendamentos,
  capacidade,
  recursos,
  sugestoes,
  onUseSlot,
}) {
  const recursosAtivos = recursos.filter((item) => item.ativo);
  const slots = montarSlots(capacidade);
  const sugestoesPorCelula = mapearSugestoes(sugestoes);

  return (
    <section className="rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
            Grade operacional
          </p>
          <h3 className="mt-2 text-lg font-black text-slate-900">
            Horarios x recursos
          </h3>
        </div>
        <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-bold text-orange-700">
          slots de {SLOT_MINUTOS} min
        </span>
      </div>

      <div className="mt-4 overflow-x-auto">
        <div
          className="grid min-w-[780px] gap-2"
          style={{ gridTemplateColumns: `90px repeat(${Math.max(recursosAtivos.length, 1)}, minmax(140px, 1fr))` }}
        >
          <div />
          {recursosAtivos.map((recurso) => (
            <HeaderRecurso key={recurso.id} recurso={recurso} />
          ))}

          {slots.map((slot) => (
            <SlotRow
              key={slot.label}
              agendamentos={agendamentos}
              recursos={recursosAtivos}
              slot={slot}
              sugestoesPorCelula={sugestoesPorCelula}
              onUseSlot={onUseSlot}
            />
          ))}
        </div>
      </div>

      {recursosAtivos.length === 0 && (
        <p className="mt-4 rounded-2xl border border-dashed border-slate-300 p-5 text-center text-sm text-slate-500">
          Cadastre recursos para visualizar a grade.
        </p>
      )}
    </section>
  );
}

function SlotRow({ agendamentos, recursos, slot, sugestoesPorCelula, onUseSlot }) {
  return (
    <>
      <div className="rounded-2xl bg-slate-100 px-3 py-3 text-xs font-black text-slate-600">
        {slot.label}
      </div>
      {recursos.map((recurso) => {
        const itens = agendamentos.filter((item) => sobrepoeSlot(item, recurso.id, slot));
        const sugestao = sugestoesPorCelula.get(`${recurso.id}-${slot.label}`);
        return (
          <GradeCell
            key={`${slot.label}-${recurso.id}`}
            itens={itens}
            recurso={recurso}
            sugestao={sugestao}
            onUseSlot={onUseSlot}
          />
        );
      })}
    </>
  );
}

function HeaderRecurso({ recurso }) {
  return (
    <div className="rounded-2xl bg-slate-900 px-3 py-3 text-white">
      <p className="text-sm font-black">{recurso.nome}</p>
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300">
        {recurso.tipo} | cap. {recurso.capacidade_simultanea}
      </p>
    </div>
  );
}

function GradeCell({ itens, recurso, sugestao, onUseSlot }) {
  const ocupado = itens.length > 0;
  return (
    <button
      type="button"
      disabled={!sugestao}
      onClick={() => sugestao && onUseSlot(sugestao)}
      className={`min-h-[74px] rounded-2xl border p-3 text-left transition ${
        ocupado
          ? "border-orange-200 bg-orange-50"
          : sugestao
          ? "border-emerald-200 bg-emerald-50 hover:border-emerald-400"
          : "border-slate-200 bg-slate-50"
      }`}
    >
      {ocupado ? (
        itens.slice(0, 2).map((item) => (
          <p key={item.id} className="truncate text-xs font-black text-slate-800">
            {item.pet_nome || `Pet #${item.pet_id}`}
          </p>
        ))
      ) : (
        <p className="text-xs font-bold text-slate-400">
          {sugestao ? "Livre para agendar" : "Sem sugestao"}
        </p>
      )}
      {itens.length > 2 && (
        <p className="mt-1 text-xs font-bold text-orange-700">
          +{itens.length - 2} agenda(s)
        </p>
      )}
      {sugestao && (
        <p className="mt-2 text-[11px] font-black uppercase tracking-[0.12em] text-emerald-700">
          usar {recurso.nome}
        </p>
      )}
    </button>
  );
}

function montarSlots(capacidade) {
  const inicio = minutos(capacidade?.janela_inicio || "08:00");
  const fim = minutos(capacidade?.janela_fim || "18:00");
  const slots = [];
  for (let cursor = inicio; cursor < fim; cursor += SLOT_MINUTOS) {
    slots.push({ inicio: cursor, fim: cursor + SLOT_MINUTOS, label: labelHora(cursor) });
  }
  return slots;
}

function mapearSugestoes(sugestoes) {
  const mapa = new Map();
  sugestoes.forEach((slot) => {
    mapa.set(`${slot.recurso_id}-${hora(slot.horario_inicio)}`, slot);
  });
  return mapa;
}

function sobrepoeSlot(agendamento, recursoId, slot) {
  if (Number(agendamento.recurso_id) !== Number(recursoId)) return false;
  const inicio = minutos(hora(agendamento.data_hora_inicio));
  const fim = minutos(hora(agendamento.data_hora_fim_prevista)) || inicio;
  return inicio < slot.fim && fim > slot.inicio;
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
