export default function CampanhasGestorHeader({
  gestorModo,
  setGestorModo,
  gestorSearch,
  setGestorSearch,
  buscarClientesGestor,
  setGestorSugestoes,
  gestorBuscando,
  gestorSugestoes,
  selecionarClienteGestor,
  gestorCampanhaTipo,
  setGestorCampanhaTipo,
  carregarClientesPorCampanha,
  gestorCampanhaCarregando,
}) {
  return (
    <div className="bg-white rounded-xl border shadow-sm p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div>
          <h2 className="font-semibold text-gray-800">Gestor de Beneficios</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {gestorModo === "cliente"
              ? "Busque um cliente para gerenciar seus beneficios."
              : "Selecione um tipo e veja todos os clientes participantes."}
          </p>
        </div>

        <div className="flex gap-2 shrink-0">
          <button
            onClick={() => setGestorModo("cliente")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              gestorModo === "cliente"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            Por Cliente
          </button>
          <button
            onClick={() => setGestorModo("campanha")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              gestorModo === "campanha"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            Por Campanha
          </button>
        </div>
      </div>

      {gestorModo === "cliente" && (
        <div className="relative max-w-md">
          <input
            type="text"
            value={gestorSearch}
            onChange={(e) => {
              setGestorSearch(e.target.value);
              buscarClientesGestor(e.target.value);
            }}
            onKeyDown={(e) => e.key === "Escape" && setGestorSugestoes([])}
            placeholder="Nome, CPF ou telefone do cliente..."
            className="w-full border rounded-lg px-3 py-2.5 text-sm"
            autoComplete="off"
          />

          {gestorBuscando && (
            <span className="absolute right-3 top-3 text-xs text-gray-400 animate-pulse">
              Buscando...
            </span>
          )}

          {gestorSugestoes.length > 0 && (
            <div className="absolute z-20 mt-1 w-full bg-white rounded-xl border shadow-xl overflow-hidden max-h-72 overflow-y-auto">
              {gestorSugestoes.map((cliente) => (
                <button
                  key={cliente.id}
                  onClick={() => selecionarClienteGestor(cliente)}
                  className="w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors border-b last:border-b-0"
                >
                  <p className="text-sm font-medium text-gray-900">
                    {cliente.nome}
                  </p>
                  <p className="text-xs text-gray-400">
                    {cliente.cpf ? `CPF: ${cliente.cpf}` : ""}
                    {cliente.cpf && cliente.telefone ? " • " : ""}
                    {cliente.telefone || ""}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {gestorModo === "campanha" && (
        <div className="flex gap-3 flex-wrap items-center">
          <select
            value={gestorCampanhaTipo}
            onChange={(e) => setGestorCampanhaTipo(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm min-w-[200px]"
          >
            <option value="carimbos">Cartao Fidelidade</option>
            <option value="cashback">Cashback (saldo positivo)</option>
            <option value="cupons">Cupons Ativos</option>
            <option value="ranking">Ranking (mes atual)</option>
          </select>
          <button
            onClick={() => carregarClientesPorCampanha(gestorCampanhaTipo)}
            disabled={gestorCampanhaCarregando}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {gestorCampanhaCarregando ? "Carregando..." : "Buscar Clientes"}
          </button>
        </div>
      )}
    </div>
  );
}
