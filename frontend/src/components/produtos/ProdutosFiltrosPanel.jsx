import FilterBar from "../ui/FilterBar";
import FornecedorSelector from "../fornecedores/FornecedorSelector";
import { CategoriaProdutoSelector, MarcaProdutoSelector } from "./CatalogoProdutoSelectors";

export default function ProdutosFiltrosPanel({
  categorias,
  filtros,
  fornecedores,
  handleFiltroChange,
  marcas,
  persistirBusca,
  setPersistirBusca,
}) {
  const fornecedorSelecionado =
    fornecedores.find((fornecedor) => String(fornecedor.id) === String(filtros.fornecedor_id)) ||
    null;

  const handleSubmit = (event) => {
    event.preventDefault();
  };

  return (
    <FilterBar id="tour-produtos-filtros" className="mb-4 md:mb-6" onSubmit={handleSubmit}>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-7 md:gap-4">
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
          <CategoriaProdutoSelector
            categorias={categorias}
            value={filtros.categoria_id}
            onChange={(valor) => handleFiltroChange("categoria_id", valor)}
            showLabel={false}
            inputClassName="rounded-lg border-gray-300"
          />
        </div>

        <div>
          <MarcaProdutoSelector
            marcas={marcas}
            value={filtros.marca_id}
            onChange={(valor) => handleFiltroChange("marca_id", valor)}
            showLabel={false}
            inputClassName="rounded-lg border-gray-300"
          />
        </div>

        <div>
          <FornecedorSelector
            fornecedores={fornecedores}
            fornecedorId={filtros.fornecedor_id}
            fornecedorSelecionado={fornecedorSelecionado}
            showLabel={false}
            placeholder="Buscar fornecedor..."
            inputClassName="rounded-lg border-gray-300"
            onInputChange={(termo) => {
              if (!termo || filtros.fornecedor_id) {
                handleFiltroChange("fornecedor_id", "");
              }
            }}
            onSelect={(fornecedor) =>
              handleFiltroChange("fornecedor_id", fornecedor?.id ? String(fornecedor.id) : "")
            }
            onClear={() => handleFiltroChange("fornecedor_id", "")}
            onFornecedorCriado={(fornecedor) =>
              handleFiltroChange("fornecedor_id", fornecedor?.id ? String(fornecedor.id) : "")
            }
          />
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

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:col-span-2">
          <label className="flex min-h-10 items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filtros.estoque_baixo}
              onChange={(event) => handleFiltroChange("estoque_baixo", event.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Estoque Baixo</span>
          </label>

          <label className="flex min-h-10 items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filtros.em_promocao}
              onChange={(event) => handleFiltroChange("em_promocao", event.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Em Promocao</span>
          </label>

          <label className="flex min-h-10 items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 cursor-pointer sm:col-span-2">
            <input
              type="checkbox"
              checked={filtros.mostrarPaisVariacoes}
              onChange={(event) => handleFiltroChange("mostrarPaisVariacoes", event.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Incluir pais, variacoes e kits</span>
          </label>

          <label
            className="flex min-h-10 items-center gap-2 cursor-pointer rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 sm:col-span-2"
            title="Quando ligado, a busca fica salva ao sair e voltar para a lista"
          >
            <input
              type="checkbox"
              checked={persistirBusca}
              onChange={(event) => setPersistirBusca(event.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-700">Persistir filtros</span>
          </label>
        </div>
      </div>
    </FilterBar>
  );
}
