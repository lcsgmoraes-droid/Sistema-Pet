export default function EvolucaoInternacaoModal({
  isOpen,
  formEvolucao,
  setFormEvolucao,
  onClose,
  onConfirm,
  salvando,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-bold text-gray-800">Registrar evolução</h2>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Temp. (°C)</label>
            <input
              type="number"
              step="0.1"
              value={formEvolucao.temperatura}
              onChange={(e) => setFormEvolucao((p) => ({ ...p, temperatura: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">FC (bpm)</label>
            <input
              type="number"
              value={formEvolucao.fc}
              onChange={(e) => setFormEvolucao((p) => ({ ...p, fc: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">FR (rpm)</label>
            <input
              type="number"
              value={formEvolucao.fr}
              onChange={(e) => setFormEvolucao((p) => ({ ...p, fr: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Observações</label>
          <textarea
            value={formEvolucao.observacoes}
            onChange={(e) => setFormEvolucao((p) => ({ ...p, observacoes: e.target.value }))}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-20"
          />
        </div>
        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={salvando}
            className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Registrar"}
          </button>
        </div>
      </div>
    </div>
  );
}
