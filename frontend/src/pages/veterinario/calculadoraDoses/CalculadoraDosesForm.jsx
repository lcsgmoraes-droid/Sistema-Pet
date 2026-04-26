import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";

export default function CalculadoraDosesForm({
  form,
  medicamentoSelecionado,
  medicamentos,
  petsDaPessoa,
  retornoNovoPet,
  selecionarMedicamento,
  selecionarPet,
  selecionarTutor,
  setCampo,
  tutorSelecionado,
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="md:col-span-2">
          <TutorAutocomplete
            label="Tutor"
            inputId="calc-dose-tutor"
            selectedTutor={tutorSelecionado}
            onSelect={selecionarTutor}
          />
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between gap-2">
            <label htmlFor="calc-dose-pet" className="block text-sm font-medium text-gray-700">Pet</label>
            <NovoPetButton
              tutorId={tutorSelecionado?.id || form.pessoa_id}
              tutorNome={tutorSelecionado?.nome}
              returnTo={retornoNovoPet}
            />
          </div>
          <select
            id="calc-dose-pet"
            value={form.pet_id}
            disabled={!form.pessoa_id}
            onChange={(event) => selecionarPet(event.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm disabled:bg-gray-100"
          >
            <option value="">{form.pessoa_id ? "Selecione o pet..." : "Selecione o tutor primeiro..."}</option>
            {petsDaPessoa.map((pet) => (
              <option key={pet.id} value={pet.id}>{pet.nome} {pet.especie ? `- ${pet.especie}` : ""}</option>
            ))}
          </select>
          {form.pessoa_id && petsDaPessoa.length === 0 && (
            <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para esta pessoa.</p>
          )}
        </div>

        <CampoNumero
          id="calc-dose-peso"
          label="Peso atual (kg)"
          step="0.01"
          value={form.peso_kg}
          onChange={(value) => setCampo("peso_kg", value)}
        />

        <div>
          <label htmlFor="calc-dose-medicamento" className="block text-sm font-medium text-gray-700 mb-1">Medicamento</label>
          <select
            id="calc-dose-medicamento"
            value={form.medicamento_id}
            onChange={(event) => selecionarMedicamento(event.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          >
            <option value="">Selecione...</option>
            {medicamentos.map((med) => (
              <option key={med.id} value={med.id}>{med.nome}</option>
            ))}
          </select>
        </div>

        <CampoNumero
          id="calc-dose-mgkg"
          label="Dose desejada (mg/kg)"
          step="0.01"
          value={form.dose_mg_kg}
          onChange={(value) => setCampo("dose_mg_kg", value)}
        />
        <CampoNumero
          id="calc-dose-frequencia"
          label="Frequencia (horas)"
          min="1"
          value={form.frequencia_horas}
          onChange={(value) => setCampo("frequencia_horas", value)}
        />
        <CampoNumero
          id="calc-dose-dias"
          label="Dias de tratamento"
          min="1"
          value={form.dias}
          onChange={(value) => setCampo("dias", value)}
        />
      </div>

      {medicamentoSelecionado && <FaixaMedicamento medicamento={medicamentoSelecionado} />}
    </div>
  );
}

function CampoNumero({ id, label, min, onChange, step, value }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        id={id}
        type="number"
        min={min}
        step={step}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
      />
    </div>
  );
}

function FaixaMedicamento({ medicamento }) {
  return (
    <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-900">
      <p className="font-semibold">Faixa cadastrada no catalogo</p>
      <p className="mt-1">
        {medicamento.dose_min_mgkg ?? "-"} a {medicamento.dose_max_mgkg ?? "-"} mg/kg
      </p>
      {medicamento.posologia_referencia && (
        <p className="mt-2 text-cyan-800">{medicamento.posologia_referencia}</p>
      )}
    </div>
  );
}
