export default function CampanhasGestorCampanhaLista({
  gestorModo,
  gestorCampanhaCarregando,
  gestorCampanhaLista,
  abrirClienteNoGestor,
}) {
  if (gestorModo !== "campanha") {
    return null;
  }

  if (gestorCampanhaCarregando) {
    return (
      <div className="text-center py-12 text-gray-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
        <p className="text-sm">Carregando clientes...</p>
      </div>
    );
  }

  if (gestorCampanhaLista === null) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
      <div className="px-6 py-3 bg-gray-50 border-b flex items-center justify-between">
        <p className="text-sm font-medium text-gray-700">
          {gestorCampanhaLista.length === 0
            ? "Nenhum cliente encontrado"
            : `${gestorCampanhaLista.length} cliente(s) encontrado(s)`}
        </p>
        <p className="text-xs text-gray-400">
          Clique em "Ver detalhes" para gerenciar
        </p>
      </div>

      {gestorCampanhaLista.length === 0 ? (
        <div className="p-10 text-center text-gray-400 text-sm">
          Nenhum cliente ativo neste tipo de campanha.
        </div>
      ) : (
        <div className="divide-y max-h-[600px] overflow-y-auto">
          {gestorCampanhaLista.map((cliente) => (
            <div
              key={cliente.id}
              className="flex items-center gap-4 px-6 py-3 hover:bg-gray-50 transition-colors"
            >
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold text-sm shrink-0">
                {cliente.nome?.[0]?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {cliente.nome}
                </p>
                <p className="text-xs text-gray-400">
                  {cliente.cpf ? `CPF: ${cliente.cpf}` : ""}
                  {cliente.cpf && cliente.telefone ? " · " : ""}
                  {cliente.telefone || ""}
                </p>
              </div>
              <span className="px-3 py-1 bg-blue-50 text-blue-700 text-xs rounded-full font-medium shrink-0">
                {cliente.detalhe}
              </span>
              <button
                onClick={() => abrirClienteNoGestor(cliente)}
                className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 font-medium shrink-0"
              >
                Ver detalhes →
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
