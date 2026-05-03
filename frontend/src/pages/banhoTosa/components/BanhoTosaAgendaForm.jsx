import { SelectField, TextField } from "../../../components/ui/FormField";
import TutorPetSelector from "../../../components/veterinario/TutorPetSelector";

export default function BanhoTosaAgendaForm({
  dataRef,
  form,
  loadingPets,
  petsDoTutor,
  saving,
  recursos = [],
  servicos,
  tutorSelecionado,
  retornoNovoPet,
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
        <TutorPetSelector
          tutorSelecionado={tutorSelecionado}
          petId={form.pet_id}
          pets={petsDoTutor}
          loadingPets={loadingPets}
          tutorInputId="bt-agenda-tutor"
          returnTo={retornoNovoPet}
          onSelectTutor={onSelectTutor}
          onSelectPet={(petId) => onChangeField("pet_id", petId)}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Data" type="date" value={dataRef} onChange={onChangeData} tone="warm" />
          <TextField label="Hora" type="time" value={form.hora} onChange={(value) => onChangeField("hora", value)} tone="warm" />
        </div>

        <SelectField label="Recurso / box" value={form.recurso_id} onChange={(value) => onChangeField("recurso_id", value)} tone="warm">
          <option value="">Sem recurso definido</option>
          {recursos.filter((item) => item.ativo).map((recurso) => (
            <option key={recurso.id} value={recurso.id}>
              {recurso.nome} - cap. {recurso.capacidade_simultanea}
            </option>
          ))}
        </SelectField>

        <SelectField label="Servico" value={form.servico_id} onChange={onChangeServico} tone="warm">
          <option value="">Banho & Tosa avulso</option>
          {servicos.filter((item) => item.ativo).map((servico) => (
            <option key={servico.id} value={servico.id}>
              {servico.nome} - {servico.duracao_padrao_minutos} min
            </option>
          ))}
        </SelectField>

        <TextField label="Valor previsto" type="number" value={form.valor_unitario} onChange={(value) => onChangeField("valor_unitario", value)} tone="warm" />
        <TextField label="Observacoes" value={form.observacoes} onChange={(value) => onChangeField("observacoes", value)} tone="warm" />
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
