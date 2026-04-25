import ProdutoEstoqueAutocomplete from "../../../components/veterinario/ProdutoEstoqueAutocomplete";

export default function InsumoRapidoInternacaoModal({
  isOpen,
  onClose,
  formInsumoRapido,
  setFormInsumoRapido,
  internacoesOrdenadas,
  veterinarios,
  insumoRapidoSelecionado,
  setInsumoRapidoSelecionado,
  onConfirm,
  salvando,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Lançar insumo rápido</h2>
            <p className="text-sm text-gray-500">
              Registre materiais ou medicamentos consumidos durante a internação com baixa automática do estoque.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar modal de insumo"
          >
            ×
          </button>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Internado *</label>
            <select
              value={formInsumoRapido.internacao_id}
              onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, internacao_id: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white"
            >
              <option value="">Selecione...</option>
              {internacoesOrdenadas.map((internacao) => (
                <option key={`insumo_internacao_${internacao.id}`} value={internacao.id}>
                  {internacao.pet_nome ?? `Pet #${internacao.pet_id}`}{internacao.box ? ` • ${internacao.box}` : ""}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Responsável *</label>
            <select
              value={formInsumoRapido.responsavel}
              onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, responsavel: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white"
            >
              <option value="">Selecione...</option>
              {veterinarios.map((vet) => (
                <option key={`insumo_vet_${vet.id}`} value={vet.nome}>
                  {vet.nome}{vet.crmv ? ` • CRMV ${vet.crmv}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-2">
            <ProdutoEstoqueAutocomplete
              selectedProduct={insumoRapidoSelecionado}
              onSelect={setInsumoRapidoSelecionado}
              helperText="Pesquise pelo nome ou código do insumo que foi consumido na internação."
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Quantidade utilizada *</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={formInsumoRapido.quantidade_utilizada}
              onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, quantidade_utilizada: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Desperdício / perda</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={formInsumoRapido.quantidade_desperdicio}
              onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, quantidade_desperdicio: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Horário do uso *</label>
            <input
              type="datetime-local"
              value={formInsumoRapido.horario_execucao}
              onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, horario_execucao: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-gray-600">Observações</label>
            <textarea
              value={formInsumoRapido.observacoes}
              onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, observacoes: e.target.value }))}
              rows={3}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              placeholder="Ex.: trocado tapete, perdido 5 mL na manipulação, pet removeu curativo..."
            />
          </div>
        </div>

        <div className="mt-6 flex gap-3">
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
            disabled={salvando}
            className="flex-1 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Registrar insumo"}
          </button>
        </div>
      </div>
    </div>
  );
}
