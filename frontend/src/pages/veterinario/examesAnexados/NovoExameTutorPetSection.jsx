import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";

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

      <div className="sm:col-span-2">
        <div className="mb-1 flex items-center justify-between gap-2">
          <label className="block text-xs font-medium text-gray-600">Pet*</label>
          <NovoPetButton
            tutorId={tutorFormSelecionado?.id}
            tutorNome={tutorFormSelecionado?.nome}
            returnTo={retornoNovoPet}
            onBeforeNavigate={onClose}
          />
        </div>
        <select
          value={form.pet_id}
          onChange={(event) => setForm((prev) => ({ ...prev, pet_id: event.target.value }))}
          disabled={!tutorFormSelecionado?.id}
          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400"
        >
          <option value="">
            {!tutorFormSelecionado?.id
              ? "Selecione o tutor primeiro..."
              : petsDoTutor.length > 0
              ? "Selecione o pet..."
              : "Nenhum pet vinculado a este tutor"}
          </option>
          {petsDoTutor.map((pet) => (
            <option key={pet.id} value={pet.id}>
              {pet.nome}
              {pet.especie ? ` (${pet.especie})` : ""}
            </option>
          ))}
        </select>
        {tutorFormSelecionado?.id && petsDoTutor.length === 0 && (
          <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para este tutor.</p>
        )}
      </div>
    </>
  );
}
