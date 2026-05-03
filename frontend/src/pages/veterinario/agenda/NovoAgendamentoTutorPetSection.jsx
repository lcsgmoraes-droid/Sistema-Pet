import TutorAutocomplete from "../../../components/TutorAutocomplete";
import PetSelector from "../../../components/pets/PetSelector";

export default function NovoAgendamentoTutorPetSection({
  carregandoPetsTutor,
  formNovo,
  onChangeCampo,
  onHideForNovoPet,
  onTutorSelect,
  petsDoTutor,
  retornoNovoPet,
  tutorSelecionado,
}) {
  return (
    <>
      <TutorAutocomplete
        label="Tutor"
        inputId="agenda-tutor"
        selectedTutor={tutorSelecionado}
        onSelect={onTutorSelect}
        placeholder="Digite o nome, CPF ou telefone do tutor..."
      />

      <PetSelector
        loadingPets={carregandoPetsTutor}
        onBeforeNovoPet={onHideForNovoPet}
        onSelectPet={(pet) => onChangeCampo("pet_id", pet ? String(pet.id) : "")}
        petId={formNovo.pet_id}
        petLabel="Pet*"
        pets={petsDoTutor}
        placeholder="Selecione o pet..."
        returnTo={retornoNovoPet}
        tutorSelecionado={tutorSelecionado}
      />
    </>
  );
}
