import FilterBar from "../ui/FilterBar";
import FornecedorSelector from "../fornecedores/FornecedorSelector";
import InputCheckTexto from "../v2/InputCheckTexto/InputCheckTexto";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import { CategoriaProdutoSelector, MarcaProdutoSelector } from "./CatalogoProdutoSelectors";
import ProdutoSelector from "./ProdutoSelector";

const OPCOES_ATIVO = [
  { value: "ativos", label: "Somente Ativos" },
  { value: "inativos", label: "Somente Inativos" },
  { value: "todos", label: "Ativos e Inativos" },
];

const OPCOES_CANAL = [
  { value: "ecommerce", label: "Canal: e-commerce" },
  { value: "app", label: "Canal: app" },
];

const OPCOES_SITUACAO_CATALOGO = [
  { value: "todos", label: "Todo catálogo online" },
  { value: "publicado", label: "Publicados no canal" },
  { value: "nao_publicado", label: "Não publicados no canal" },
  { value: "bloqueado", label: "Bloqueados" },
  { value: "esgotado", label: "Esgotados" },
  { value: "pendencias", label: "Vendáveis com dados faltantes" },
  { value: "pronto", label: "Completos" },
];

const OPCOES_ESTOQUE = [
  { value: "todos", label: "Todo estoque" },
  { value: "com_estoque", label: "Com estoque" },
  { value: "sem_estoque", label: "Sem estoque" },
];

const OPCOES_IMAGEM = [
  { value: "todas", label: "Todas as fotos" },
  { value: "com_foto", label: "Com foto" },
  { value: "sem_foto", label: "Sem foto" },
];

const OPCOES_ORDENACAO = [
  { value: "recentes", label: "Últimos cadastrados" },
  { value: "estoque_desc", label: "Maior estoque" },
  { value: "estoque_asc", label: "Menor estoque" },
];

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
      <div className="grid grid-cols-1 gap-3 md:grid-cols-4 md:gap-4 xl:grid-cols-6">
        <div id="tour-produtos-busca" className="md:col-span-2">
          <ProdutoSelector
            placeholder="Buscar por SKU, nome ou qualquer EAN..."
            value={filtros.busca}
            onChange={(valor) => handleFiltroChange("busca", valor)}
            showSuggestions={false}
            inputClassName="w-full border-gray-300"
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
          <InputCombobox
            opcoes={OPCOES_ATIVO}
            value={filtros.ativo}
            onChange={(valor) => handleFiltroChange("ativo", valor)}
            placeholder="Status do produto"
            permitirLimpar={false}
          />
        </div>

        <div>
          <InputCombobox
            opcoes={OPCOES_CANAL}
            value={filtros.catalogo_online_canal}
            onChange={(valor) => handleFiltroChange("catalogo_online_canal", valor)}
            placeholder="Canal do catálogo online"
            permitirLimpar={false}
          />
        </div>

        <div className="md:col-span-2">
          <InputCombobox
            opcoes={OPCOES_SITUACAO_CATALOGO}
            value={filtros.catalogo_online_situacao}
            onChange={(valor) => handleFiltroChange("catalogo_online_situacao", valor)}
            placeholder="Situação no catálogo online"
            permitirLimpar={false}
          />
        </div>

        <div>
          <InputCombobox
            opcoes={OPCOES_ESTOQUE}
            value={filtros.estoque_situacao}
            onChange={(valor) => handleFiltroChange("estoque_situacao", valor)}
            placeholder="Filtrar por estoque"
            permitirLimpar={false}
          />
        </div>

        <div>
          <InputCombobox
            opcoes={OPCOES_IMAGEM}
            value={filtros.imagem_situacao}
            onChange={(valor) => handleFiltroChange("imagem_situacao", valor)}
            placeholder="Filtrar por foto"
            permitirLimpar={false}
          />
        </div>

        <div>
          <InputCombobox
            opcoes={OPCOES_ORDENACAO}
            value={filtros.ordenacao}
            onChange={(valor) => handleFiltroChange("ordenacao", valor)}
            placeholder="Ordenar produtos"
            permitirLimpar={false}
          />
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:col-span-4 md:grid-cols-4 xl:col-span-6">
          <div className="flex min-h-10 items-center rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
            <InputCheckTexto
              id="produtos-filtro-estoque-baixo"
              checked={filtros.estoque_baixo}
              onChange={(checked) => handleFiltroChange("estoque_baixo", checked)}
            >
              Estoque Baixo
            </InputCheckTexto>
          </div>

          <div className="flex min-h-10 items-center rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
            <InputCheckTexto
              id="produtos-filtro-em-promocao"
              checked={filtros.em_promocao}
              onChange={(checked) => handleFiltroChange("em_promocao", checked)}
            >
              Em Promoção
            </InputCheckTexto>
          </div>

          <div className="flex min-h-10 items-center rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 sm:col-span-2 md:col-span-1">
            <InputCheckTexto
              id="produtos-filtro-pais-variacoes"
              checked={filtros.mostrarPaisVariacoes}
              onChange={(checked) => handleFiltroChange("mostrarPaisVariacoes", checked)}
            >
              Incluir pais, variações e kits
            </InputCheckTexto>
          </div>

          <div
            className="flex min-h-10 items-center rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 sm:col-span-2 md:col-span-1"
            title="Quando ligado, a busca fica salva ao sair e voltar para a lista"
          >
            <InputCheckTexto
              id="produtos-filtro-persistir-busca"
              checked={persistirBusca}
              onChange={(checked) => setPersistirBusca(checked)}
            >
              <span className="text-xs">Persistir filtros</span>
            </InputCheckTexto>
          </div>
        </div>
      </div>
    </FilterBar>
  );
}
