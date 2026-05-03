import TutorAutocomplete from "../../../components/TutorAutocomplete";
import PetSelector from "../../../components/pets/PetSelector";

export default function RegistrarVacinaTutorPetSection({
  form,
  onBeforeNovoPet,
  onSelecionarTutor,
  onSetCampo,
  petsDaPessoa,
  retornoNovoPet,
  tutorFormSelecionado,
}) {
  return (
    <>
      <div className="col-span-2">
        <TutorAutocomplete
          label="Pessoa (tutor) *"
          inputId="vacinas-tutor-form"
          selectedTutor={tutorFormSelecionado}
          onSelect={onSelecionarTutor}
        />
      </div>

      <PetSelector
        className="col-span-2"
        disabled={!form.pessoa_id}
        emptyStateLabel="Nenhum pet ativo encontrado para esta pessoa."
        onBeforeNovoPet={onBeforeNovoPet}
        onSelectPet={(pet) => onSetCampo("pet_id", pet ? String(pet.id) : "")}
        petId={form.pet_id}
        petLabel="Pet da pessoa *"
        pets={petsDaPessoa}
        placeholder="Selecione..."
        returnTo={retornoNovoPet}
        tutorId={tutorFormSelecionado?.id || form.pessoa_id}
        tutorNome={tutorFormSelecionado?.nome}
        tutorSelecionado={tutorFormSelecionado}
      />
    </>
  );
}
