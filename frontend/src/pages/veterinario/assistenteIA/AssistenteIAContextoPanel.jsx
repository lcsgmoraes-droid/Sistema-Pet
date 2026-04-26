import { Calculator, FlaskConical, Link2, Pill, Stethoscope } from "lucide-react";
import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";
import { assistenteIaCss, formatarLabelConsulta } from "./assistenteIAUtils";

function BotaoModo({ ativo, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 text-sm rounded-lg border ${
        ativo
          ? "bg-cyan-600 text-white border-cyan-600"
          : "bg-white text-gray-600 border-gray-200"
      }`}
    >
      <span className="inline-flex items-center gap-2">{children}</span>
    </button>
  );
}

function CampoMedicamento({ id, label, value, onChange, placeholder }) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-gray-600 mb-1">
        {label}
      </label>
      <div className="relative">
        <Pill size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={`${assistenteIaCss.input} pl-9`}
          placeholder={placeholder}
        />
      </div>
    </div>
  );
}

export default function AssistenteIAContextoPanel({
  consultaId,
  consultaSelecionada,
  consultas,
  exameId,
  exameSelecionado,
  exames,
  med1,
  med2,
  modo,
  onAbrirConsulta,
  onSelecionarPet,
  onSelecionarTutor,
  pesoKg,
  petId,
  petsDoTutor,
  retornoNovoPet,
  setConsultaId,
  setExameId,
  setMed1,
  setMed2,
  setModo,
  setPesoKg,
  tutorSelecionado,
}) {
  return (
    <>
      <div className="flex flex-wrap gap-2">
        <BotaoModo ativo={modo === "atendimento"} onClick={() => setModo("atendimento")}>
          <Stethoscope size={14} /> Vincular atendimento
        </BotaoModo>
        <BotaoModo ativo={modo === "livre"} onClick={() => setModo("livre")}>
          <FlaskConical size={14} /> Conversa livre
        </BotaoModo>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="md:col-span-2">
          <TutorAutocomplete
            label="Tutor"
            inputId="vet-ia-tutor"
            selectedTutor={tutorSelecionado}
            onSelect={onSelecionarTutor}
          />
        </div>

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
            <option value="">
              {tutorSelecionado?.id ? "Selecione o pet..." : "Selecione o tutor primeiro..."}
            </option>
            {petsDoTutor.map((pet) => (
              <option key={pet.id} value={pet.id}>
                {pet.nome}
                {pet.especie ? ` (${pet.especie})` : ""}
              </option>
            ))}
          </select>
          {tutorSelecionado?.id && petsDoTutor.length === 0 && (
            <p className="mt-2 text-xs text-amber-600">
              Nenhum pet ativo encontrado para este tutor.
            </p>
          )}
        </div>

        {modo === "atendimento" && (
          <>
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
          </>
        )}
      </div>

      {(consultaSelecionada || exameSelecionado) && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {consultaSelecionada && (
            <div className="rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-cyan-900">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-cyan-600">
                    Consulta vinculada
                  </p>
                  <p className="font-semibold">#{consultaSelecionada.id}</p>
                  <p className="text-xs text-cyan-700">
                    {consultaSelecionada.motivo_consulta || "Sem motivo informado"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onAbrirConsulta(consultaSelecionada.id)}
                  className="inline-flex items-center gap-2 rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-medium text-cyan-700 hover:bg-cyan-100"
                >
                  <Link2 size={13} />
                  Abrir consulta
                </button>
              </div>
            </div>
          )}

          {exameSelecionado && (
            <div className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-900">
              <p className="text-xs font-medium uppercase tracking-wide text-violet-600">
                Exame vinculado
              </p>
              <p className="font-semibold">
                #{exameSelecionado.id} • {exameSelecionado.nome || exameSelecionado.tipo || "Exame"}
              </p>
              <p className="text-xs text-violet-700">
                {exameSelecionado.arquivo_nome
                  ? `Arquivo: ${exameSelecionado.arquivo_nome}`
                  : "Sem arquivo anexado ainda"}
              </p>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <label htmlFor="vet-ia-peso" className="block text-xs font-medium text-gray-600 mb-1">
            Peso (kg) para cálculo de dose
          </label>
          <div className="relative">
            <Calculator size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              id="vet-ia-peso"
              value={pesoKg}
              onChange={(event) => setPesoKg(event.target.value)}
              className={`${assistenteIaCss.input} pl-9`}
              placeholder="Ex: 12,5"
            />
          </div>
        </div>

        <CampoMedicamento
          id="vet-ia-med1"
          label="Medicamento 1 (opcional)"
          value={med1}
          onChange={setMed1}
          placeholder="Ex: amoxicilina"
        />
        <CampoMedicamento
          id="vet-ia-med2"
          label="Medicamento 2 (opcional)"
          value={med2}
          onChange={setMed2}
          placeholder="Ex: prednisolona"
        />
      </div>
    </>
  );
}
