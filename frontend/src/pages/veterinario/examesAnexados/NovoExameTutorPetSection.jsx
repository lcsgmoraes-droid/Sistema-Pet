import TutorAutocomplete from "../../../components/TutorAutocomplete";
import PetSelector from "../../../components/pets/PetSelector";

export default function NovoExameTutorPetSection({
  form,
  onClose,
  petsDoTutor,
  retornoNovoPet,
  setForm,
  setTutorFormSelecionado,
  tutorFormSelecionado,
}) {
  return (
    <>
      <div className="sm:col-span-2">
        <TutorAutocomplete
          label="Tutor"
          inputId="exame-tutor"
          selectedTutor={tutorFormSelecionado}
          onSelect={(tutor) => {
            setTutorFormSelecionado(tutor);
            setForm((prev) => ({ ...prev, pet_id: "" }));
          }}
          placeholder="Digite o nome, CPF ou telefone do tutor..."
        />
      </div>

      <PetSelector
        className="sm:col-span-2"
        onBeforeNovoPet={onClose}
        onSelectPet={(pet) =>
          setForm((prev) => ({ ...prev, pet_id: pet ? String(pet.id) : "" }))
        }
        petId={form.pet_id}
        petLabel="Pet*"
        pets={petsDoTutor}
        placeholder="Selecione o pet..."
        returnTo={retornoNovoPet}
        tutorSelecionado={tutorFormSelecionado}
      />
    </>
  );
}
