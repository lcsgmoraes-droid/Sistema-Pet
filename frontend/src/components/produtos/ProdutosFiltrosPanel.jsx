import React from "react";

export default function ProdutosFiltrosPanel({
  categorias,
  filtros,
  fornecedores,
  handleFiltroChange,
  marcas,
  persistirBusca,
  setPersistirBusca,
}) {
  return (
    <div id="tour-produtos-filtros" className="bg-white rounded-lg shadow-sm p-4 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
        <div id="tour-produtos-busca" className="md:col-span-2">
          <input
            type="text"
            placeholder="Buscar por codigo, nome ou codigo de barras..."
            value={filtros.busca}
            onChange={(event) => handleFiltroChange("busca", event.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <select
            value={filtros.categoria_id}
            onChange={(event) => handleFiltroChange("categoria_id", event.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Todas as Categorias</option>
            {categorias.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.categoria_pai_id ? "  -> " : ""}
                {cat.nome}
              </option>
            ))}
          </select>
        </div>

        <div>
          <select
            value={filtros.marca_id}
            onChange={(event) => handleFiltroChange("marca_id", event.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Todas as Marcas</option>
            {marcas.map((marca) => (
              <option key={marca.id} value={marca.id}>
                {marca.nome}
              </option>
            ))}
          </select>
        </div>

        <div>
          <select
            value={filtros.fornecedor_id}
            onChange={(event) => handleFiltroChange("fornecedor_id", event.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Todos os Fornecedores</option>
            {fornecedores.map((fornecedor) => (
              <option key={fornecedor.id} value={fornecedor.id}>
                {fornecedor.nome}
              </option>
            ))}
          </select>
        </div>

        <div>
          <select
            value={filtros.ativo}
            onChange={(event) => handleFiltroChange("ativo", event.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="ativos">Somente Ativos</option>
            <option value="inativos">Somente Inativos</option>
            <option value="todos">Ativos e Inativos</option>
          </select>
        </div>

        <div className="flex gap-4 items-center flex-wrap md:col-span-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filtros.estoque_baixo}
              onChange={(event) => handleFiltroChange("estoque_baixo", event.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Estoque Baixo</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filtros.em_promocao}
              onChange={(event) => handleFiltroChange("em_promocao", event.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Em Promocao</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filtros.mostrarPaisVariacoes}
              onChange={(event) =>
                handleFiltroChange("mostrarPaisVariacoes", event.target.checked)
              }
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Mostrar Pais, Variacoes e Kits</span>
          </label>

          <label
            className="flex items-center gap-2 cursor-pointer px-2 py-1 rounded-md border border-gray-200 bg-gray-50"
            title="Quando ligado, a busca fica salva ao sair e voltar para a lista"
          >
            <input
              type="checkbox"
              checked={persistirBusca}
              onChange={(event) => setPersistirBusca(event.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-700">Persistir pesquisa</span>
          </label>
        </div>
      </div>
    </div>
  );
}
