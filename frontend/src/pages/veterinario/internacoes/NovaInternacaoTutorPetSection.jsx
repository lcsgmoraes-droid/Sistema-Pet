import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";

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
      <div>
        <div className="mb-1 flex items-center justify-between gap-2">
          <label className="block text-xs font-medium text-gray-600">Pet da pessoa *</label>
          <NovoPetButton
            tutorId={formNova.pessoa_id}
            tutorNome={tutorAtualInternacao?.nome}
            returnTo={retornoNovoPet}
            onBeforeNavigate={onHideForNovoPet}
          />
        </div>
        <select
          value={formNova.pet_id}
          onChange={(event) => setFormNova((prev) => ({ ...prev, pet_id: event.target.value }))}
          disabled={!formNova.pessoa_id}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white disabled:opacity-60"
        >
          <option value="">Selecione...</option>
          {petsDaPessoa.map((pet) => (
            <option key={pet.id} value={pet.id}>
              {pet.nome}{pet.especie ? ` (${pet.especie})` : ""}
            </option>
          ))}
        </select>
        {formNova.pessoa_id && petsDaPessoa.length === 0 && (
          <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para esta pessoa.</p>
        )}
      </div>
    </>
  );
}
