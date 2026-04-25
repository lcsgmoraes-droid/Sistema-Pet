export default function ConcluirProcedimentoModal({
  procedimento,
  baiaExibicao,
  formFeito,
  setFormFeito,
  veterinarios,
  onClose,
  onConfirm,
  salvando,
}) {
  if (!procedimento) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-bold text-gray-800">Concluir procedimento</h2>
        <div className="bg-purple-50 border border-purple-200 rounded-lg px-3 py-2">
          <p className="text-xs text-purple-700 font-semibold">{procedimento.pet_nome}</p>
          <p className="text-sm font-bold text-purple-900">{procedimento.medicamento}</p>
          <p className="text-xs text-purple-700">Dose: {procedimento.dose || "—"} • Baia: {baiaExibicao}</p>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Informe o que estava previsto, quanto realmente foi administrado e quanto virou desperdício/excesso. Assim o registro clínico fica fiel ao que aconteceu no atendimento.
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Responsável veterinário *</label>
          <select
            value={formFeito.feito_por}
            onChange={(e) => setFormFeito((p) => ({ ...p, feito_por: e.target.value }))}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value="">Selecione...</option>
            {veterinarios.map((vet) => (
              <option key={vet.id} value={vet.nome}>
                {vet.nome}{vet.crmv ? ` - CRMV ${vet.crmv}` : ""}
              </option>
            ))}
            {formFeito.feito_por && !veterinarios.some((vet) => vet.nome === formFeito.feito_por) && (
              <option value={formFeito.feito_por}>{formFeito.feito_por}</option>
            )}
          </select>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Qtd. prevista</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={formFeito.quantidade_prevista}
              onChange={(e) => setFormFeito((p) => ({ ...p, quantidade_prevista: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Unidade</label>
            <input
              type="text"
              value={formFeito.unidade_quantidade}
              onChange={(e) => setFormFeito((p) => ({ ...p, unidade_quantidade: e.target.value }))}
              placeholder="mL, mg, comp, un..."
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Qtd. efetivamente feita</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={formFeito.quantidade_executada}
              onChange={(e) => setFormFeito((p) => ({ ...p, quantidade_executada: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Desperdício / excesso</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={formFeito.quantidade_desperdicio}
              onChange={(e) => setFormFeito((p) => ({ ...p, quantidade_desperdicio: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Horário da execução *</label>
          <input
            type="datetime-local"
            value={formFeito.horario_execucao}
            onChange={(e) => setFormFeito((p) => ({ ...p, horario_execucao: e.target.value }))}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Observação da execução (opcional)</label>
          <textarea
            value={formFeito.observacao_execucao}
            onChange={(e) => setFormFeito((p) => ({ ...p, observacao_execucao: e.target.value }))}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-20"
            placeholder="Ex.: pet aceitou bem, sem reação"
          />
        </div>
        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={salvando}
            className="flex-1 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Confirmar feito"}
          </button>
        </div>
      </div>
    </div>
  );
}
