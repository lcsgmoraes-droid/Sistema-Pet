import { Activity, AlertCircle, X } from "lucide-react";
import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";
import {
  STATUS_BADGE,
  STATUS_COLOR,
  STATUS_LABEL,
  TIPO_ACAO,
  TIPO_BADGE,
  TIPO_LABEL,
  TIPO_OPTIONS,
  normalizarTipoAgendamento,
} from "./agendaUtils";

export default function NovoAgendamentoModal({
  isOpen,
  agendamentoEditandoId,
  erroNovo,
  tutorSelecionado,
  formNovo,
  setFormNovo,
  petsDoTutor,
  carregandoPetsTutor,
  retornoNovoPet,
  veterinarios,
  consultorios,
  dicaTipoSelecionado,
  tipoSelecionado,
  motivoPlaceholderPorTipo,
  conflitoHorarioSelecionado,
  diagnosticoConflitoSelecionado,
  veterinarioSelecionadoModal,
  consultorioSelecionadoModal,
  agendaDiaModal,
  horariosAgendaModal,
  carregandoAgendaDiaModal,
  abrindoAgendamentoId,
  salvandoNovo,
  bloqueioCamposAgendamento,
  onClose,
  onTutorSelect,
  onHideForNovoPet,
  onConfiguracoesVet,
  onOpenAgendamento,
  onConfirm,
}) {
  if (!isOpen) return null;

  function atualizarCampo(campo, valor) {
    setFormNovo((prev) => ({ ...prev, [campo]: valor }));
  }

  const textoPetVazio = !tutorSelecionado?.id
    ? "Selecione o tutor primeiro..."
    : carregandoPetsTutor
    ? "Carregando pets..."
    : petsDoTutor.length > 0
    ? "Selecione o pet..."
    : "Nenhum pet vinculado a este tutor";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-5xl rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-bold text-gray-800">
              {agendamentoEditandoId ? "Editar agendamento" : "Novo agendamento"}
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Escolha o tipo do servico, veja a agenda do dia e abra depois o fluxo certo com pet e tutor ja prontos.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar modal"
          >
            <X size={18} />
          </button>
        </div>

        {erroNovo && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            <AlertCircle size={16} />
            <span>{erroNovo}</span>
          </div>
        )}

        <div className="mt-5 grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
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
                onChange={(e) => atualizarCampo("pet_id", e.target.value)}
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
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Veterinario*</label>
                <select
                  value={formNovo.veterinario_id}
                  onChange={(e) => atualizarCampo("veterinario_id", e.target.value)}
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400"
                  disabled={veterinarios.length === 0}
                >
                  <option value="">
                    {veterinarios.length > 0 ? "Selecione o veterinario..." : "Nenhum veterinario cadastrado"}
                  </option>
                  {veterinarios.map((vet) => (
                    <option key={vet.id} value={vet.id}>
                      {vet.nome}
                    </option>
                  ))}
                </select>
                {veterinarios.length === 0 && (
                  <p className="mt-1 text-xs text-amber-600">
                    Cadastre um veterinario em Pessoas para vincular o atendimento corretamente.
                  </p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Consultorio*</label>
                <select
                  value={formNovo.consultorio_id}
                  onChange={(e) => atualizarCampo("consultorio_id", e.target.value)}
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400"
                  disabled={consultorios.length === 0}
                >
                  <option value="">
                    {consultorios.length > 0 ? "Selecione o consultorio..." : "Nenhum consultorio cadastrado"}
                  </option>
                  {consultorios.map((consultorio) => (
                    <option key={consultorio.id} value={consultorio.id}>
                      {consultorio.nome}
                    </option>
                  ))}
                </select>
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
                onChange={(e) => atualizarCampo("tipo", e.target.value)}
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
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Data*</label>
                <input
                  type="date"
                  value={formNovo.data}
                  onChange={(e) => atualizarCampo("data", e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Horario*</label>
                <input
                  type="time"
                  value={formNovo.hora}
                  onChange={(e) => atualizarCampo("hora", e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
            </div>

            {conflitoHorarioSelecionado && (
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
            )}

            {!conflitoHorarioSelecionado &&
              formNovo.hora &&
              diagnosticoConflitoSelecionado.outrosNoHorario.length > 0 && (
                <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
                  Ja existe outro atendimento nesse horario, mas com profissional/sala diferentes.
                </div>
              )}

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Motivo</label>
              <input
                type="text"
                value={formNovo.motivo}
                onChange={(e) => atualizarCampo("motivo", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder={motivoPlaceholderPorTipo[tipoSelecionado]}
              />
            </div>

            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={formNovo.emergencia}
                onChange={(e) => atualizarCampo("emergencia", e.target.checked)}
                className="rounded"
              />
              <span className="text-sm text-gray-700">Emergencia</span>
            </label>
          </div>

          <div className="space-y-4">
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-gray-800">Agenda do dia</p>
                  <p className="text-xs text-gray-500">
                    {formNovo.data
                      ? new Date(`${formNovo.data}T12:00:00`).toLocaleDateString("pt-BR", {
                          weekday: "long",
                          day: "2-digit",
                          month: "long",
                          year: "numeric",
                        })
                      : "Selecione uma data"}
                  </p>
                </div>
                <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-gray-600">
                  {agendaDiaModal.length} agendamento(s)
                </span>
              </div>

              <div className="mt-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
                  Horarios sugeridos
                </p>
                <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                  {horariosAgendaModal.map((slot) => (
                    <button
                      key={slot.horario}
                      type="button"
                      onClick={() => atualizarCampo("hora", slot.horario)}
                      className={`rounded-lg border px-2 py-2 text-xs font-medium transition-colors ${
                        formNovo.hora === slot.horario
                          ? slot.livre
                            ? "border-blue-600 bg-blue-600 text-white"
                            : "border-amber-500 bg-amber-500 text-white"
                          : slot.livre
                          ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                          : "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
                      }`}
                    >
                      <div>{slot.horario}</div>
                      <div className="mt-0.5 text-[10px] opacity-80">
                        {slot.livre ? "Livre" : `${slot.ocupados.length} ocupado(s)`}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <p className="mb-3 text-sm font-semibold text-gray-800">Compromissos do dia selecionado</p>
              {carregandoAgendaDiaModal ? (
                <div className="text-sm text-gray-500">Carregando agenda do dia...</div>
              ) : agendaDiaModal.length === 0 ? (
                <div className="rounded-lg border border-dashed border-emerald-200 bg-emerald-50 px-3 py-4 text-sm text-emerald-700">
                  Nenhum compromisso neste dia. A agenda esta livre.
                </div>
              ) : (
                <div className="max-h-[300px] space-y-2 overflow-y-auto pr-1">
                  {agendaDiaModal.map((ag) => {
                    const tipoAgendamento = normalizarTipoAgendamento(ag.tipo);

                    return (
                      <button
                        key={ag.id}
                        type="button"
                        onClick={() => onOpenAgendamento(ag)}
                        className={`w-full rounded-lg border px-3 py-2 text-left ${
                          STATUS_COLOR[ag.status] ?? "border-l-gray-200 bg-white"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-gray-800">
                            {String(ag.data_hora || "").slice(11, 16) || "--:--"}
                          </span>
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                              STATUS_BADGE[ag.status] ?? "bg-gray-100 text-gray-600"
                            }`}
                          >
                            {STATUS_LABEL[ag.status] ?? ag.status}
                          </span>
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                              TIPO_BADGE[tipoAgendamento] ?? "bg-gray-100 text-gray-600"
                            }`}
                          >
                            {TIPO_LABEL[tipoAgendamento] ?? "Consulta"}
                          </span>
                          {ag.is_emergencia && <Activity size={12} className="ml-auto text-red-500" />}
                        </div>
                        <div className="mt-1 text-sm font-medium text-gray-700">
                          {ag.pet_nome ?? `Pet #${String(ag.pet_id ?? "").slice(0, 6)}`}
                        </div>
                        <div className="text-[11px] text-gray-500">
                          {[ag.veterinario_nome, ag.consultorio_nome].filter(Boolean).join(" • ") ||
                            "Sem profissional/sala"}
                        </div>
                        <div className="text-xs text-gray-500">{ag.motivo ?? "Sem motivo informado"}</div>
                        <div className="mt-2 text-[11px] font-medium text-blue-600">
                          {abrindoAgendamentoId === ag.id
                            ? "Abrindo fluxo..."
                            : TIPO_ACAO[tipoAgendamento] ?? "Abrir atendimento"}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex gap-3 pt-5">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={
              salvandoNovo ||
              !formNovo.pet_id ||
              !formNovo.data ||
              !formNovo.hora ||
              bloqueioCamposAgendamento.veterinario ||
              bloqueioCamposAgendamento.consultorio ||
              conflitoHorarioSelecionado
            }
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {salvandoNovo ? "Salvando..." : agendamentoEditandoId ? "Salvar alteracoes" : "Confirmar"}
          </button>
        </div>
      </div>
    </div>
  );
}
