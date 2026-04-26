import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";

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

      <div className="col-span-2">
        <div className="mb-1 flex items-center justify-between gap-2">
          <label htmlFor="vacinas-pet-form" className="block text-xs font-medium text-gray-600">
            Pet da pessoa *
          </label>
          <NovoPetButton
            tutorId={tutorFormSelecionado?.id || form.pessoa_id}
            tutorNome={tutorFormSelecionado?.nome}
            returnTo={retornoNovoPet}
            onBeforeNavigate={onBeforeNovoPet}
          />
        </div>
        <select
          id="vacinas-pet-form"
          value={form.pet_id}
          onChange={(event) => onSetCampo("pet_id", event.target.value)}
          disabled={!form.pessoa_id}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white disabled:opacity-60"
        >
          <option value="">Selecione...</option>
          {petsDaPessoa.map((pet) => (
            <option key={pet.id} value={pet.id}>
              {pet.nome}
              {pet.especie ? ` (${pet.especie})` : ""}
            </option>
          ))}
        </select>
        {form.pessoa_id && petsDaPessoa.length === 0 && (
          <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para esta pessoa.</p>
        )}
      </div>
    </>
  );
}
