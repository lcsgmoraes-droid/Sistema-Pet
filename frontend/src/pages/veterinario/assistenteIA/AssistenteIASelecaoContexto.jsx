import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";
import { assistenteIaCss, formatarLabelConsulta } from "./assistenteIAUtils";

export default function AssistenteIASelecaoContexto({
  consultaId,
  consultas,
  exameId,
  exames,
  modo,
  onSelecionarPet,
  onSelecionarTutor,
  petId,
  petsDoTutor,
  retornoNovoPet,
  setConsultaId,
  setExameId,
  tutorSelecionado,
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
      <div className="md:col-span-2">
        <TutorAutocomplete
          label="Tutor"
          inputId="vet-ia-tutor"
          selectedTutor={tutorSelecionado}
          onSelect={onSelecionarTutor}
        />
      </div>

      <PetSelector
        onSelecionarPet={onSelecionarPet}
        petId={petId}
        petsDoTutor={petsDoTutor}
        retornoNovoPet={retornoNovoPet}
        tutorSelecionado={tutorSelecionado}
      />

      {modo === "atendimento" && (
        <>
          <ConsultaSelector consultaId={consultaId} consultas={consultas} setConsultaId={setConsultaId} />
          <ExameSelector exameId={exameId} exames={exames} setExameId={setExameId} />
        </>
      )}
    </div>
  );
}

function PetSelector({ onSelecionarPet, petId, petsDoTutor, retornoNovoPet, tutorSelecionado }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-2">
        <label htmlFor="vet-ia-pet" className="block text-xs font-medium text-gray-600">
          Pet (opcional)
        </label>
        <NovoPetButton
          tutorId={tutorSelecionado?.id}
          tutorNome={tutorSelecionado?.nome}
          returnTo={retornoNovoPet}
        />
      </div>
      <select
        id="vet-ia-pet"
        value={petId}
        onChange={(event) => onSelecionarPet(event.target.value)}
        className={assistenteIaCss.select}
        disabled={!tutorSelecionado?.id}
      >
        <option value="">{tutorSelecionado?.id ? "Selecione o pet..." : "Selecione o tutor primeiro..."}</option>
        {petsDoTutor.map((pet) => (
          <option key={pet.id} value={pet.id}>
            {pet.nome}
            {pet.especie ? ` (${pet.especie})` : ""}
          </option>
        ))}
      </select>
      {tutorSelecionado?.id && petsDoTutor.length === 0 && (
        <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para este tutor.</p>
      )}
    </div>
  );
}

function ConsultaSelector({ consultaId, consultas, setConsultaId }) {
  return (
    <div>
      <label htmlFor="vet-ia-consulta" className="block text-xs font-medium text-gray-600 mb-1">
        Consulta (opcional)
      </label>
      <select
        id="vet-ia-consulta"
        value={consultaId}
        onChange={(event) => setConsultaId(event.target.value)}
        className={assistenteIaCss.select}
      >
        <option value="">Sem consulta</option>
        {consultas.map((consulta) => (
          <option key={consulta.id} value={consulta.id}>
            {formatarLabelConsulta(consulta)}
          </option>
        ))}
      </select>
    </div>
  );
}

function ExameSelector({ exameId, exames, setExameId }) {
  return (
    <div>
      <label htmlFor="vet-ia-exame" className="block text-xs font-medium text-gray-600 mb-1">
        Exame (opcional)
      </label>
      <select
        id="vet-ia-exame"
        value={exameId}
        onChange={(event) => setExameId(event.target.value)}
        className={assistenteIaCss.select}
      >
        <option value="">Sem exame</option>
        {exames.map((exame) => (
          <option key={exame.id} value={exame.id}>
            {exame.nome || exame.tipo || `Exame #${exame.id}`}
          </option>
        ))}
      </select>
    </div>
  );
}
