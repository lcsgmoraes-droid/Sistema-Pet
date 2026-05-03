import TutorAutocomplete from "../../../components/TutorAutocomplete";
import PetSelector from "../../../components/pets/PetSelector";

export default function NovaInternacaoTutorPetSection({
  formNova,
  onHideForNovoPet,
  petsDaPessoa,
  retornoNovoPet,
  setFormNova,
  setTutorNovaSelecionado,
  tutorAtualInternacao,
  tutorNovaSelecionado,
}) {
  return (
    <>
      <div>
        <TutorAutocomplete
          label="Pessoa (tutor) *"
          inputId="internacao-tutor"
          selectedTutor={tutorNovaSelecionado}
          onSelect={(cliente) => {
            setTutorNovaSelecionado(cliente);
            setFormNova((prev) => ({
              ...prev,
              pessoa_id: cliente?.id ? String(cliente.id) : "",
              pet_id: "",
            }));
          }}
        />
      </div>
      <PetSelector
        disabled={!formNova.pessoa_id}
        emptyStateLabel="Nenhum pet ativo encontrado para esta pessoa."
        onBeforeNovoPet={onHideForNovoPet}
        onSelectPet={(pet) =>
          setFormNova((prev) => ({ ...prev, pet_id: pet ? String(pet.id) : "" }))
        }
        petId={formNova.pet_id}
        petLabel="Pet da pessoa *"
        pets={petsDaPessoa}
        placeholder="Selecione..."
        returnTo={retornoNovoPet}
        tutorId={formNova.pessoa_id}
        tutorNome={tutorAtualInternacao?.nome}
        tutorSelecionado={tutorNovaSelecionado}
      />
    </>
  );
}
