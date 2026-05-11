import FornecedorSelector from "../fornecedores/FornecedorSelector";
import AutocompleteSelect from "../ui/AutocompleteSelect";

function ProdutosBalancoFiltros({
  filtros,
  fornecedores,
  marcas,
  onAtualizarFiltro,
  onAplicarFiltros,
}) {
  const fornecedorSelecionado =
    fornecedores.find(
      (fornecedor) => String(fornecedor.id) === String(filtros.fornecedor_id),
    ) || null;

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

        <AutocompleteSelect
          options={marcas}
          value={filtros.marca_id}
          onChange={(valor) => onAtualizarFiltro("marca_id", valor)}
          showLabel={false}
          placeholder="Todas as marcas"
          searchPlaceholder="Buscar marca..."
          inputClassName="rounded-lg border-gray-300"
          getOptionLabel={(marca) => marca.nome || ""}
        />

        <FornecedorSelector
          fornecedores={fornecedores}
          fornecedorId={filtros.fornecedor_id}
          fornecedorSelecionado={fornecedorSelecionado}
          showLabel={false}
          placeholder="Buscar fornecedor..."
          inputClassName="rounded-lg border-gray-300"
          onInputChange={(termo) => {
            if (!termo || filtros.fornecedor_id) {
              onAtualizarFiltro("fornecedor_id", "");
            }
          }}
          onSelect={(fornecedor) =>
            onAtualizarFiltro("fornecedor_id", fornecedor?.id ? String(fornecedor.id) : "")
          }
          onClear={() => onAtualizarFiltro("fornecedor_id", "")}
          onFornecedorCriado={(fornecedor) =>
            onAtualizarFiltro("fornecedor_id", fornecedor?.id ? String(fornecedor.id) : "")
          }
        />

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
