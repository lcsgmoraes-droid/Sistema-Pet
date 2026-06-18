import TutorAutocomplete from "../../../components/TutorAutocomplete";
import PetSelector from "../../../components/pets/PetSelector";
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
        allowEmpty
        emptyOptionLabel="Sem pet"
        onSelectPet={(pet) => onSelecionarPet(pet ? String(pet.id) : "")}
        petId={petId}
        pets={petsDoTutor}
        petLabel="Pet (opcional)"
        placeholder="Selecione o pet..."
        returnTo={retornoNovoPet}
        tutorSelecionado={tutorSelecionado}
      />

      {modo === "atendimento" && (
        <>
          <ConsultaSelector
            consultaId={consultaId}
            consultas={consultas}
            setConsultaId={setConsultaId}
          />
          <ExameSelector exameId={exameId} exames={exames} setExameId={setExameId} />
        </>
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
