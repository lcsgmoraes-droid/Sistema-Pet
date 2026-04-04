export default function CampanhasCarimboManualModal({
  fidModalManual,
  setFidModalManual,
  fidClienteId,
  fidManualNota,
  setFidManualNota,
  lancarCarimboManual,
  fidLancandoManual,
}) {
  if (!fidModalManual) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">
            Lancar carimbo manual
          </h3>
          <button
            onClick={() => setFidModalManual(false)}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            x
          </button>
        </div>
        <div className="px-6 py-4 space-y-3">
          <p className="text-sm text-gray-500">
            Cliente <strong>#{fidClienteId}</strong> - esse carimbo sera
            registrado como manual, sem vinculo com uma venda.
          </p>
          <div>
            <label
              htmlFor="fid-nota"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Observacao (opcional)
            </label>
            <input
              id="fid-nota"
              type="text"
              value={fidManualNota}
              onChange={(e) => setFidManualNota(e.target.value)}
              placeholder="Ex: Conversao de cartao fisico"
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div className="px-6 py-4 border-t flex gap-3 justify-end">
          <button
            onClick={() => setFidModalManual(false)}
            className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
          >
            Cancelar
          </button>
          <button
            onClick={lancarCarimboManual}
            disabled={fidLancandoManual}
            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          >
            {fidLancandoManual ? "Lancando..." : "Confirmar carimbo"}
          </button>
        </div>
      </div>
    </div>
  );
}
