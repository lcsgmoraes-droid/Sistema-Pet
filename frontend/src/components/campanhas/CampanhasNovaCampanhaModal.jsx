export default function CampanhasNovaCampanhaModal({
  modalCriarCampanha,
  setModalCriarCampanha,
  novaCampanha,
  setNovaCampanha,
  erroCriarCampanha,
  criarCampanha,
  criandoCampanha,
}) {
  if (!modalCriarCampanha) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Nova campanha</h3>
          <button
            onClick={() => setModalCriarCampanha(false)}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            x
          </button>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div>
            <label
              htmlFor="nc-nome"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Nome da campanha
            </label>
            <input
              id="nc-nome"
              type="text"
              placeholder="Ex: Recompra Rapida Verao"
              value={novaCampanha.name}
              onChange={(e) =>
                setNovaCampanha((p) => ({ ...p, name: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label
              htmlFor="nc-tipo"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Tipo
            </label>
            <select
              id="nc-tipo"
              value={novaCampanha.campaign_type}
              onChange={(e) =>
                setNovaCampanha((p) => ({
                  ...p,
                  campaign_type: e.target.value,
                }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              <option value="inactivity">Clientes inativos</option>
              <option value="quick_repurchase">Recompra rapida</option>
            </select>
          </div>
          <p className="text-xs text-gray-500">
            Os parametros poderao ser configurados depois de criar a campanha.
          </p>
          {erroCriarCampanha && (
            <p className="text-sm text-red-600">{erroCriarCampanha}</p>
          )}
        </div>
        <div className="px-6 py-4 border-t flex gap-3 justify-end">
          <button
            onClick={() => setModalCriarCampanha(false)}
            className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
          >
            Cancelar
          </button>
          <button
            onClick={criarCampanha}
            disabled={criandoCampanha}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {criandoCampanha ? "Criando..." : "Criar campanha"}
          </button>
        </div>
      </div>
    </div>
  );
}
