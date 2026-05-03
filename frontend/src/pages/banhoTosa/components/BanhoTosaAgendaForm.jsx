import { Plus } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
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
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-4">
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
          <TextField label="Data" type="date" value={dataRef} onChange={onChangeData} />
          <TextField label="Hora" type="time" value={form.hora} onChange={(value) => onChangeField("hora", value)} />
        </div>

        <SelectField label="Recurso / box" value={form.recurso_id} onChange={(value) => onChangeField("recurso_id", value)}>
          <option value="">Sem recurso definido</option>
          {recursos.filter((item) => item.ativo).map((recurso) => (
            <option key={recurso.id} value={recurso.id}>
              {recurso.nome} - cap. {recurso.capacidade_simultanea}
            </option>
          ))}
        </SelectField>

        <SelectField label="Servico" value={form.servico_id} onChange={onChangeServico}>
          <option value="">Banho & Tosa avulso</option>
          {servicos.filter((item) => item.ativo).map((servico) => (
            <option key={servico.id} value={servico.id}>
              {servico.nome} - {servico.duracao_padrao_minutos} min
            </option>
          ))}
        </SelectField>

        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Valor previsto" type="number" value={form.valor_unitario} onChange={(value) => onChangeField("valor_unitario", value)} />
          <TextField label="Observacoes" value={form.observacoes} onChange={(value) => onChangeField("observacoes", value)} />
        </div>
      </div>

      <div className="flex justify-end">
        <ActionButton icon={Plus} intent="create" loading={saving} size="md" type="submit">
          Criar agendamento
        </ActionButton>
      </div>
    </form>
  );
}
