import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";

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
  const textoPetVazio = !tutorSelecionado?.id
    ? "Selecione o tutor primeiro..."
    : carregandoPetsTutor
    ? "Carregando pets..."
    : petsDoTutor.length > 0
    ? "Selecione o pet..."
    : "Nenhum pet vinculado a este tutor";

  return (
    <>
      <TutorAutocomplete
        label="Tutor"
        inputId="agenda-tutor"
        selectedTutor={tutorSelecionado}
        onSelect={onTutorSelect}
        placeholder="Digite o nome, CPF ou telefone do tutor..."
      />

      <div>
        <div className="mb-1 flex items-center justify-between gap-2">
          <label className="block text-xs font-medium text-gray-600">Pet*</label>
          <NovoPetButton
            tutorId={tutorSelecionado?.id}
            tutorNome={tutorSelecionado?.nome}
            returnTo={retornoNovoPet}
            onBeforeNavigate={onHideForNovoPet}
          />
        </div>
        <select
          value={formNovo.pet_id}
          onChange={(event) => onChangeCampo("pet_id", event.target.value)}
          disabled={!tutorSelecionado?.id || carregandoPetsTutor}
          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400"
        >
          <option value="">{textoPetVazio}</option>
          {petsDoTutor.map((pet) => (
            <option key={pet.id} value={pet.id}>
              {pet.nome}
              {pet.especie ? ` (${pet.especie})` : ""}
            </option>
          ))}
        </select>

        {tutorSelecionado?.id && !carregandoPetsTutor && petsDoTutor.length === 0 && (
          <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
            <p className="text-xs text-amber-700">
              Nenhum pet encontrado para {tutorSelecionado.nome}.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
