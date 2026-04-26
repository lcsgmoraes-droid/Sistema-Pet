export default function AgendaProcedimentoForm({
  agendaForm,
  setAgendaForm,
  internacoesOrdenadas,
  internacaoSelecionadaAgenda,
  salvando,
  onAdicionarProcedimentoAgenda,
  onAbrirInsumoRapido,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-700">Novo procedimento / lembrete</p>
          <p className="mt-1 text-xs text-gray-500">
            Preencha o que estava previsto para o paciente: horario, nome do medicamento/procedimento,
            dose clinica, quantidade prevista e via. Se quiser apenas baixar um material usado na rotina,
            use o botao de insumo rapido.
          </p>
        </div>
        <button
          type="button"
          onClick={() => onAbrirInsumoRapido(agendaForm.internacao_id)}
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
        >
          + Lancar insumo rapido
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <select
          value={agendaForm.internacao_id}
          onChange={(event) => setAgendaForm((prev) => ({ ...prev, internacao_id: event.target.value }))}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
        >
          <option value="">Selecione o internado...</option>
          {internacoesOrdenadas.map((internacao) => (
            <option key={internacao.id} value={internacao.id}>
              {internacao.pet_nome ?? `Pet #${internacao.pet_id}`}
              {internacao.box ? ` (${internacao.box})` : ""}
            </option>
          ))}
        </select>
        <input
          type="datetime-local"
          value={agendaForm.horario}
          onChange={(event) => setAgendaForm((prev) => ({ ...prev, horario: event.target.value }))}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
        />
        <input
          type="text"
          placeholder="Medicamento / procedimento"
          value={agendaForm.medicamento}
          onChange={(event) => setAgendaForm((prev) => ({ ...prev, medicamento: event.target.value }))}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
        />
        <input
          type="text"
          placeholder="Dose"
          value={agendaForm.dose}
          onChange={(event) => setAgendaForm((prev) => ({ ...prev, dose: event.target.value }))}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
        />
        <input
          type="number"
          min="0"
          step="0.01"
          placeholder="Qtd. prevista"
          value={agendaForm.quantidade_prevista}
          onChange={(event) => setAgendaForm((prev) => ({ ...prev, quantidade_prevista: event.target.value }))}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
        />
        <input
          type="text"
          placeholder="Unidade (mL, mg, comp, un...)"
          value={agendaForm.unidade_quantidade}
          onChange={(event) => setAgendaForm((prev) => ({ ...prev, unidade_quantidade: event.target.value }))}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
        />
        <input
          type="text"
          placeholder="Via (oral, IV, IM...)"
          value={agendaForm.via}
          onChange={(event) => setAgendaForm((prev) => ({ ...prev, via: event.target.value }))}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
        />
        <input
          type="text"
          value={agendaForm.internacao_id ? (internacaoSelecionadaAgenda?.box || "Sem baia") : "Selecione um internado"}
          disabled
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-600"
        />
        <input
          type="number"
          min="0"
          placeholder="Lembrete (min)"
          value={agendaForm.lembrete_min}
          onChange={(event) => setAgendaForm((prev) => ({ ...prev, lembrete_min: event.target.value }))}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
        />
        <input
          type="text"
          placeholder="Observacoes"
          value={agendaForm.observacoes}
          onChange={(event) => setAgendaForm((prev) => ({ ...prev, observacoes: event.target.value }))}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm md:col-span-2"
        />
        <button
          type="button"
          onClick={onAdicionarProcedimentoAgenda}
          disabled={salvando}
          className="bg-purple-600 hover:bg-purple-700 text-white rounded-lg px-3 py-2 text-sm disabled:opacity-60"
        >
          {salvando ? "Salvando..." : "Adicionar na agenda"}
        </button>
      </div>
    </div>
  );
}
