import TutorPetSelector from "../../../components/veterinario/TutorPetSelector";

export default function PetConsultaSelector({
  isEdicao,
  form,
  setCampo,
  renderCampo,
  tutorSelecionado,
  listaPetsExpandida,
  setListaPetsExpandida,
  petsDoTutor,
  abrirModalNovoPet,
}) {
  return (
    <>
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          {renderCampo("Pet", true)(
            <TutorPetSelector
              showTutorField={false}
              showPetLabel={false}
              autoExpandOnTutorChange={false}
              tutorSelecionado={tutorSelecionado}
              petId={form.pet_id}
              pets={petsDoTutor}
              disabledPet={isEdicao}
              expanded={Boolean(listaPetsExpandida && tutorSelecionado && !isEdicao)}
              onExpandedChange={setListaPetsExpandida}
              onSelectPet={(petId) => setCampo("pet_id", petId)}
              onNovoPetClick={abrirModalNovoPet}
            />
          )}
        </div>
      </div>

      {!isEdicao && tutorSelecionado && petsDoTutor.length === 0 ? (
        <p className="text-xs text-amber-600">
          Nenhum pet ativo vinculado a esse tutor.
        </p>
      ) : null}
    </>
  );
}
