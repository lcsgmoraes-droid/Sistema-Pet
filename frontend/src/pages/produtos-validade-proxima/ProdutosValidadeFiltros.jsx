import FornecedorSelector from "../../components/fornecedores/FornecedorSelector";
import {
  CategoriaProdutoSelector,
  MarcaProdutoSelector,
} from "../../components/produtos/CatalogoProdutoSelectors";
import ActionButton from "../../components/ui/ActionButton";

export default function ProdutosValidadeFiltros({ controller }) {
  const { categorias, fornecedores, marcas, departamentos } = controller.catalogos;
  const filtros = controller.filtrosForm;

  return (
    <form
      onSubmit={controller.aplicarFiltros}
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm md:p-5"
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <div className="xl:col-span-2">
          <label className="mb-1 block text-sm font-medium text-gray-700">Busca</label>
          <input
            type="text"
            value={filtros.busca}
            onChange={(event) => controller.atualizarFiltro("busca", event.target.value)}
            placeholder="Produto, codigo, SKU ou lote"
            className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <SelectField
          label="Janela"
          value={filtros.dias}
          onChange={(event) => controller.atualizarFiltro("dias", Number(event.target.value))}
          options={[30, 60, 90, 120, 180].map((dia) => [`${dia}`, `Ate ${dia} dias`])}
        />
        <SelectField
          label="Status"
          value={filtros.status_validade}
          onChange={(event) => controller.atualizarFiltro("status_validade", event.target.value)}
          options={[
            ["proximos", "Somente proximos"],
            ["vencidos", "Somente vencidos"],
            ["todos", "Vencidos + proximos"],
          ]}
        />
        <SelectField
          label="Ordenacao"
          value={filtros.ordenacao}
          onChange={(event) => controller.atualizarFiltro("ordenacao", event.target.value)}
          options={[
            ["validade_asc", "Validade mais proxima"],
            ["validade_desc", "Validade mais distante"],
            ["quantidade_desc", "Maior quantidade"],
            ["valor_desc", "Maior valor em risco"],
          ]}
        />

        <CategoriaProdutoSelector
          categorias={categorias}
          label="Categoria"
          value={filtros.categoria_id}
          onChange={(valor) => controller.atualizarFiltro("categoria_id", valor)}
          inputClassName="rounded-xl border-gray-300 py-2.5"
        />
        <MarcaProdutoSelector
          marcas={marcas}
          label="Marca"
          value={filtros.marca_id}
          onChange={(valor) => controller.atualizarFiltro("marca_id", valor)}
          inputClassName="rounded-xl border-gray-300 py-2.5"
        />
        <SelectField
          label="Setor"
          value={filtros.departamento_id}
          onChange={(event) => controller.atualizarFiltro("departamento_id", event.target.value)}
          options={[
            ["", "Todos os setores"],
            ...departamentos.map((departamento) => [departamento.id, departamento.nome]),
          ]}
        />
        <FornecedorSelector
          fornecedores={fornecedores}
          fornecedorId={filtros.fornecedor_id}
          fornecedorSelecionado={controller.fornecedorFiltroSelecionado}
          value={filtros.fornecedor_busca}
          placeholder="Buscar fornecedor..."
          inputClassName="rounded-xl border-gray-300 py-2.5"
          onInputChange={controller.alterarFornecedorBusca}
          onSelect={controller.selecionarFornecedorFiltro}
          onClear={controller.limparFornecedorFiltro}
          onFornecedorCriado={controller.selecionarFornecedorFiltro}
        />
      </div>

      <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={filtros.apenas_com_estoque}
              onChange={(event) =>
                controller.atualizarFiltro("apenas_com_estoque", event.target.checked)
              }
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Somente lotes com saldo
          </label>

          <div className="flex items-center gap-2 text-sm text-gray-700">
            <span>Itens por pagina</span>
            <select
              value={filtros.page_size}
              onChange={(event) =>
                controller.atualizarFiltro("page_size", Number(event.target.value))
              }
              className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              {[20, 50, 100].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <ActionButton onClick={controller.limparFiltros} tone="soft">
            Limpar filtros
          </ActionButton>
          <ActionButton type="submit" intent="edit">
            Atualizar painel
          </ActionButton>
        </div>
      </div>
    </form>
  );
}

function SelectField({ label, onChange, options, value }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      <select
        value={value}
        onChange={onChange}
        className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
      >
        {options.map(([optionValue, labelText]) => (
          <option key={optionValue} value={optionValue}>
            {labelText}
          </option>
        ))}
      </select>
    </div>
  );
}
