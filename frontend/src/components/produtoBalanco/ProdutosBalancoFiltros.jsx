function ProdutosBalancoFiltros({
  filtros,
  fornecedores,
  marcas,
  onAtualizarFiltro,
  onAplicarFiltros,
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <input
          type="text"
          value={filtros.busca}
          onChange={(e) => onAtualizarFiltro("busca", e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              onAplicarFiltros();
            }
          }}
          placeholder="Buscar por nome, codigo, codigo de barras..."
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        />

        <select
          value={filtros.marca_id}
          onChange={(e) => onAtualizarFiltro("marca_id", e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Todas as marcas</option>
          {marcas.map((marca) => (
            <option key={marca.id} value={marca.id}>
              {marca.nome}
            </option>
          ))}
        </select>

        <select
          value={filtros.fornecedor_id}
          onChange={(e) => onAtualizarFiltro("fornecedor_id", e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Todos os fornecedores</option>
          {fornecedores.map((fornecedor) => (
            <option key={fornecedor.id} value={fornecedor.id}>
              {fornecedor.nome}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={onAplicarFiltros}
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-3 py-2 text-sm font-medium"
        >
          Atualizar lista
        </button>
      </div>
    </div>
  );
}

export default ProdutosBalancoFiltros;
