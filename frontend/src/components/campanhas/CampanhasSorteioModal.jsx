export default function CampanhasSorteioModal({
  modalSorteio,
  setModalSorteio,
  novoSorteio,
  setNovoSorteio,
  erroCriarSorteio,
  criarSorteio,
  criandoSorteio,
}) {
  if (!modalSorteio) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Novo sorteio</h3>
          <button
            onClick={() => setModalSorteio(false)}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            x
          </button>
        </div>
        <div className="px-6 py-4 space-y-3">
          <div>
            <label
              htmlFor="s-nome"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Nome do sorteio
            </label>
            <input
              id="s-nome"
              type="text"
              placeholder="Ex: Sorteio de Marco"
              value={novoSorteio.name}
              onChange={(e) =>
                setNovoSorteio((p) => ({ ...p, name: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label
              htmlFor="s-premio"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Premio
            </label>
            <input
              id="s-premio"
              type="text"
              placeholder="Ex: Kit banho e tosa gratis"
              value={novoSorteio.prize_description}
              onChange={(e) =>
                setNovoSorteio((p) => ({
                  ...p,
                  prize_description: e.target.value,
                }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label
              htmlFor="s-nivel"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Nivel minimo elegivel (opcional)
            </label>
            <select
              id="s-nivel"
              value={novoSorteio.rank_filter}
              onChange={(e) =>
                setNovoSorteio((p) => ({
                  ...p,
                  rank_filter: e.target.value,
                }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              <option value="">Todos os clientes</option>
              <option value="bronze">Bronze+</option>
              <option value="silver">Prata+</option>
              <option value="gold">Ouro+</option>
              <option value="platinum">Diamante+</option>
              <option value="diamond">Platina</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="s-data"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Data do sorteio (opcional)
            </label>
            <input
              id="s-data"
              type="date"
              value={novoSorteio.draw_date}
              onChange={(e) =>
                setNovoSorteio((p) => ({ ...p, draw_date: e.target.value }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label
              htmlFor="s-desc"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Descricao (opcional)
            </label>
            <textarea
              id="s-desc"
              rows={2}
              value={novoSorteio.description}
              onChange={(e) =>
                setNovoSorteio((p) => ({
                  ...p,
                  description: e.target.value,
                }))
              }
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={novoSorteio.auto_execute}
              onChange={(e) =>
                setNovoSorteio((p) => ({
                  ...p,
                  auto_execute: e.target.checked,
                }))
              }
              className="w-4 h-4 rounded"
            />
            <span className="text-sm text-gray-700">
              Executar automaticamente na data do sorteio
            </span>
          </label>
          {erroCriarSorteio && (
            <p className="text-sm text-red-600">{erroCriarSorteio}</p>
          )}
        </div>
        <div className="px-6 py-4 border-t flex gap-3 justify-end">
          <button
            onClick={() => setModalSorteio(false)}
            className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
          >
            Cancelar
          </button>
          <button
            onClick={criarSorteio}
            disabled={criandoSorteio}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
          >
            {criandoSorteio ? "Criando..." : "Criar sorteio"}
          </button>
        </div>
      </div>
    </div>
  );
}
