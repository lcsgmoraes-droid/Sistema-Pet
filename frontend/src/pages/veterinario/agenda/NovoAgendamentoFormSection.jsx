import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";
import { TIPO_OPTIONS } from "./agendaUtils";

export default function NovoAgendamentoFormSection({
  carregandoPetsTutor,
  conflitoHorarioSelecionado,
  consultorioSelecionadoModal,
  consultorios,
  diagnosticoConflitoSelecionado,
  dicaTipoSelecionado,
  formNovo,
  motivoPlaceholderPorTipo,
  onChangeCampo,
  onConfiguracoesVet,
  onHideForNovoPet,
  onTutorSelect,
  petsDoTutor,
  retornoNovoPet,
  tipoSelecionado,
  tutorSelecionado,
  veterinarioSelecionadoModal,
  veterinarios,
}) {
  const textoPetVazio = !tutorSelecionado?.id
    ? "Selecione o tutor primeiro..."
    : carregandoPetsTutor
    ? "Carregando pets..."
    : petsDoTutor.length > 0
    ? "Selecione o pet..."
    : "Nenhum pet vinculado a este tutor";

  return (
    <div className="space-y-3">
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

      <div className="grid gap-3 sm:grid-cols-2">
        <AgendamentoSelect
          alerta={
            veterinarios.length === 0
              ? "Cadastre um veterinario em Pessoas para vincular o atendimento corretamente."
              : ""
          }
          disabled={veterinarios.length === 0}
          label="Veterinario*"
          onChange={(valor) => onChangeCampo("veterinario_id", valor)}
          options={veterinarios}
          placeholder={veterinarios.length > 0 ? "Selecione o veterinario..." : "Nenhum veterinario cadastrado"}
          value={formNovo.veterinario_id}
        />

        <div>
          <AgendamentoSelect
            disabled={consultorios.length === 0}
            label="Consultorio*"
            onChange={(valor) => onChangeCampo("consultorio_id", valor)}
            options={consultorios}
            placeholder={consultorios.length > 0 ? "Selecione o consultorio..." : "Nenhum consultorio cadastrado"}
            value={formNovo.consultorio_id}
          />
          {consultorios.length === 0 && (
            <div className="mt-2 flex items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              <p className="text-xs text-amber-700">
                Cadastre os consultorios para a agenda alertar conflito de sala.
              </p>
              <button
                type="button"
                onClick={onConfiguracoesVet}
                className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100"
              >
                Configurar
              </button>
            </div>
          )}
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Tipo de servico*</label>
        <select
          value={formNovo.tipo}
          onChange={(event) => onChangeCampo("tipo", event.target.value)}
          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm"
        >
          {TIPO_OPTIONS.map((tipo) => (
            <option key={tipo.value} value={tipo.value}>
              {tipo.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-500">{dicaTipoSelecionado}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <CampoAgenda
          label="Data*"
          type="date"
          value={formNovo.data}
          onChange={(valor) => onChangeCampo("data", valor)}
        />
        <CampoAgenda
          label="Horario*"
          type="time"
          value={formNovo.hora}
          onChange={(valor) => onChangeCampo("hora", valor)}
        />
      </div>

      <ConflitosHorario
        conflitoHorarioSelecionado={conflitoHorarioSelecionado}
        consultorioSelecionadoModal={consultorioSelecionadoModal}
        diagnosticoConflitoSelecionado={diagnosticoConflitoSelecionado}
        formNovo={formNovo}
        veterinarioSelecionadoModal={veterinarioSelecionadoModal}
      />

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Motivo</label>
        <input
          type="text"
          value={formNovo.motivo}
          onChange={(event) => onChangeCampo("motivo", event.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          placeholder={motivoPlaceholderPorTipo[tipoSelecionado]}
        />
      </div>

      <label className="flex cursor-pointer items-center gap-2">
        <input
          type="checkbox"
          checked={formNovo.emergencia}
          onChange={(event) => onChangeCampo("emergencia", event.target.checked)}
          className="rounded"
        />
        <span className="text-sm text-gray-700">Emergencia</span>
      </label>

    </div>
  );
}

function AgendamentoSelect({ alerta = "", disabled, label, onChange, options, placeholder, value }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400"
        disabled={disabled}
      >
        <option value="">{placeholder}</option>
        {options.map((item) => (
          <option key={item.id} value={item.id}>
            {item.nome}
          </option>
        ))}
      </select>
      {alerta && <p className="mt-1 text-xs text-amber-600">{alerta}</p>}
    </div>
  );
}

function CampoAgenda({ label, onChange, type, value }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
      />
    </div>
  );
}

function ConflitosHorario({
  conflitoHorarioSelecionado,
  consultorioSelecionadoModal,
  diagnosticoConflitoSelecionado,
  formNovo,
  veterinarioSelecionadoModal,
}) {
  if (conflitoHorarioSelecionado) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
        {diagnosticoConflitoSelecionado.conflitosVeterinario.length > 0 && (
          <p>
            {veterinarioSelecionadoModal?.nome || "O veterinario selecionado"} ja possui paciente nesse horario.
          </p>
        )}
        {diagnosticoConflitoSelecionado.conflitosConsultorio.length > 0 && (
          <p>
            {consultorioSelecionadoModal?.nome || "O consultorio selecionado"} ja esta reservado nesse horario.
          </p>
        )}
        <p className="mt-1">Escolha outro horario, profissional ou consultorio para continuar.</p>
      </div>
    );
  }

  if (!formNovo.hora || diagnosticoConflitoSelecionado.outrosNoHorario.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
      Ja existe outro atendimento nesse horario, mas com profissional/sala diferentes.
    </div>
  );
}
