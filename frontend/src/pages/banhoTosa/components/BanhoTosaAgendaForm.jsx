import TutorAutocomplete from "../../../components/TutorAutocomplete";

export default function BanhoTosaAgendaForm({
  dataRef,
  form,
  loadingPets,
  petsDoTutor,
  saving,
  recursos = [],
  servicos,
  tutorSelecionado,
  onChangeData,
  onChangeField,
  onChangeServico,
  onSelectTutor,
  onSubmit,
}) {
  return (
    <form
      onSubmit={onSubmit}
      className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm"
    >
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
        Agenda
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-900">
        Novo agendamento
      </h2>

      <div className="mt-5 space-y-4">
        <TutorAutocomplete
          label="Tutor"
          inputId="bt-agenda-tutor"
          selectedTutor={tutorSelecionado}
          onSelect={onSelectTutor}
          placeholder="Digite nome, CPF ou telefone do tutor..."
        />

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
            Pet
          </span>
          <select
            value={form.pet_id}
            disabled={!tutorSelecionado?.id || loadingPets}
            onChange={(event) => onChangeField("pet_id", event.target.value)}
            className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100 disabled:text-slate-400"
          >
            <option value="">
              {!tutorSelecionado?.id
                ? "Selecione o tutor primeiro"
                : loadingPets
                ? "Carregando pets..."
                : "Selecione o pet"}
            </option>
            {petsDoTutor.map((pet) => (
              <option key={pet.id} value={pet.id}>
                {pet.nome} {pet.especie ? `(${pet.especie})` : ""}
              </option>
            ))}
          </select>
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Data" type="date" value={dataRef} onChange={onChangeData} />
          <TextField label="Hora" type="time" value={form.hora} onChange={(value) => onChangeField("hora", value)} />
        </div>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
            Recurso / box
          </span>
          <select
            value={form.recurso_id}
            onChange={(event) => onChangeField("recurso_id", event.target.value)}
            className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
          >
            <option value="">Sem recurso definido</option>
            {recursos.filter((item) => item.ativo).map((recurso) => (
              <option key={recurso.id} value={recurso.id}>
                {recurso.nome} - cap. {recurso.capacidade_simultanea}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
            Servico
          </span>
          <select
            value={form.servico_id}
            onChange={(event) => onChangeServico(event.target.value)}
            className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
          >
            <option value="">Banho & Tosa avulso</option>
            {servicos.filter((item) => item.ativo).map((servico) => (
              <option key={servico.id} value={servico.id}>
                {servico.nome} - {servico.duracao_padrao_minutos} min
              </option>
            ))}
          </select>
        </label>

        <TextField label="Valor previsto" type="number" value={form.valor_unitario} onChange={(value) => onChangeField("valor_unitario", value)} />
        <TextField label="Observacoes" value={form.observacoes} onChange={(value) => onChangeField("observacoes", value)} />
      </div>

      <button
        type="submit"
        disabled={saving}
        className="mt-6 w-full rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
      >
        {saving ? "Agendando..." : "Criar agendamento"}
      </button>
    </form>
  );
}

function TextField({ label, value, onChange, type = "text" }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </span>
      <input
        type={type}
        step={type === "number" ? "0.01" : undefined}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}
