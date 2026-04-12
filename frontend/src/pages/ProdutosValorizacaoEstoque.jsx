import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import {
  formatarMoeda,
  getRelatorioValorizacaoEstoque,
} from "../api/produtos";
import useProdutosCatalogos from "../hooks/useProdutosCatalogos";

const ITENS_POR_PAGINA_INICIAL = 50;

const filtrosIniciais = {
  busca: "",
  fornecedor_id: "",
  marca_id: "",
  departamento_id: "",
  apenas_com_estoque: true,
  page_size: ITENS_POR_PAGINA_INICIAL,
};

const formatarQuantidade = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number(valor || 0));

function ResumoCard({ titulo, valor, descricao, destaque = "blue" }) {
  const estilos = {
    blue: "border-blue-100 bg-blue-50 text-blue-900",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-900",
    amber: "border-amber-100 bg-amber-50 text-amber-900",
    violet: "border-violet-100 bg-violet-50 text-violet-900",
  };

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${estilos[destaque] || estilos.blue}`}>
      <p className="text-sm font-medium opacity-80">{titulo}</p>
      <p className="mt-2 text-2xl font-bold">{valor}</p>
      <p className="mt-2 text-xs opacity-75">{descricao}</p>
    </div>
  );
}

export default function ProdutosValorizacaoEstoque() {
  const navigate = useNavigate();
  const { fornecedores, marcas, departamentos } = useProdutosCatalogos();

  const [loading, setLoading] = useState(false);
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [filtrosForm, setFiltrosForm] = useState(filtrosIniciais);
  const [filtrosAplicados, setFiltrosAplicados] = useState(filtrosIniciais);
  const [dados, setDados] = useState({
    items: [],
    total: 0,
    page: 1,
    page_size: ITENS_POR_PAGINA_INICIAL,
    pages: 0,
    totais: {
      total_produtos: 0,
      total_itens_estoque: 0,
      valor_custo_total: 0,
      valor_venda_total: 0,
      margem_potencial_total: 0,
    },
  });

  useEffect(() => {
    void carregarRelatorio(filtrosAplicados, paginaAtual);
  }, [filtrosAplicados, paginaAtual]);

  const carregarRelatorio = async (filtros, pagina) => {
    try {
      setLoading(true);
      const params = {
        page: pagina,
        page_size: Number(filtros.page_size) || ITENS_POR_PAGINA_INICIAL,
        apenas_com_estoque: filtros.apenas_com_estoque,
      };

      if (filtros.busca.trim()) params.busca = filtros.busca.trim();
      if (filtros.fornecedor_id) params.fornecedor_id = filtros.fornecedor_id;
      if (filtros.marca_id) params.marca_id = filtros.marca_id;
      if (filtros.departamento_id) params.departamento_id = filtros.departamento_id;

      const response = await getRelatorioValorizacaoEstoque(params);
      setDados(response.data);
    } catch (error) {
      console.error("Erro ao carregar relatorio de valorizacao:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel carregar o relatorio de valorizacao.",
      );
      setDados((prev) => ({
        ...prev,
        items: [],
        total: 0,
        pages: 0,
        totais: {
          total_produtos: 0,
          total_itens_estoque: 0,
          valor_custo_total: 0,
          valor_venda_total: 0,
          margem_potencial_total: 0,
        },
      }));
    } finally {
      setLoading(false);
    }
  };

  const atualizarFiltro = (campo, valor) => {
    setFiltrosForm((prev) => ({
      ...prev,
      [campo]: valor,
    }));
  };

  const aplicarFiltros = (event) => {
    event.preventDefault();
    setPaginaAtual(1);
    setFiltrosAplicados({
      ...filtrosForm,
      page_size: Number(filtrosForm.page_size) || ITENS_POR_PAGINA_INICIAL,
    });
  };

  const limparFiltros = () => {
    setPaginaAtual(1);
    setFiltrosForm(filtrosIniciais);
    setFiltrosAplicados(filtrosIniciais);
  };

  const inicioItem =
    dados.total === 0 ? 0 : (dados.page - 1) * dados.page_size + 1;
  const fimItem =
    dados.total === 0 ? 0 : Math.min(dados.page * dados.page_size, dados.total);
  const totalPaginas = dados.pages || 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Valorizacao de Estoque
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-gray-600">
            Veja quanto vale o seu estoque com filtros por fornecedor, marca e
            setor. Os cards mostram o total em custo e o potencial de venda do
            estoque filtrado.
          </p>
        </div>

        <button
          onClick={() => navigate("/produtos")}
          className="inline-flex items-center justify-center rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
        >
          Voltar para produtos
        </button>
      </div>

      <form
        onSubmit={aplicarFiltros}
        className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm"
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <div className="xl:col-span-2">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Busca
            </label>
            <input
              type="text"
              value={filtrosForm.busca}
              onChange={(event) => atualizarFiltro("busca", event.target.value)}
              placeholder="Nome, codigo, SKU ou codigo de barras"
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Fornecedor
            </label>
            <select
              value={filtrosForm.fornecedor_id}
              onChange={(event) =>
                atualizarFiltro("fornecedor_id", event.target.value)
              }
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">Todos os fornecedores</option>
              {fornecedores.map((fornecedor) => (
                <option key={fornecedor.id} value={fornecedor.id}>
                  {fornecedor.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Marca
            </label>
            <select
              value={filtrosForm.marca_id}
              onChange={(event) => atualizarFiltro("marca_id", event.target.value)}
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">Todas as marcas</option>
              {marcas.map((marca) => (
                <option key={marca.id} value={marca.id}>
                  {marca.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Setor
            </label>
            <select
              value={filtrosForm.departamento_id}
              onChange={(event) =>
                atualizarFiltro("departamento_id", event.target.value)
              }
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">Todos os setores</option>
              {departamentos.map((departamento) => (
                <option key={departamento.id} value={departamento.id}>
                  {departamento.nome}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <label className="inline-flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={filtrosForm.apenas_com_estoque}
                onChange={(event) =>
                  atualizarFiltro("apenas_com_estoque", event.target.checked)
                }
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Somente itens com estoque
            </label>

            <div className="flex items-center gap-2 text-sm text-gray-700">
              <span>Itens por pagina</span>
              <select
                value={filtrosForm.page_size}
                onChange={(event) =>
                  atualizarFiltro("page_size", Number(event.target.value))
                }
                className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                {[25, 50, 100, 200].map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={limparFiltros}
              className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Limpar filtros
            </button>
            <button
              type="submit"
              className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700"
            >
              Atualizar relatorio
            </button>
          </div>
        </div>
      </form>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ResumoCard
          titulo="Valor em custo"
          valor={formatarMoeda(dados.totais.valor_custo_total)}
          descricao="Total investido no estoque filtrado."
          destaque="blue"
        />
        <ResumoCard
          titulo="Valor em venda"
          valor={formatarMoeda(dados.totais.valor_venda_total)}
          descricao="Potencial bruto de faturamento do estoque."
          destaque="emerald"
        />
        <ResumoCard
          titulo="Margem potencial"
          valor={formatarMoeda(dados.totais.margem_potencial_total)}
          descricao="Diferenca entre preco de venda e custo do estoque."
          destaque="amber"
        />
        <ResumoCard
          titulo="Quantidade em estoque"
          valor={formatarQuantidade(dados.totais.total_itens_estoque)}
          descricao={`${dados.totais.total_produtos || 0} produto(s) no filtro atual.`}
          destaque="violet"
        />
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-gray-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Produtos filtrados
            </h2>
            <p className="text-sm text-gray-500">
              {dados.total === 0
                ? "Nenhum produto encontrado."
                : `Mostrando ${inicioItem} a ${fimItem} de ${dados.total} produto(s).`}
            </p>
          </div>

          {totalPaginas > 1 && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPaginaAtual((prev) => Math.max(1, prev - 1))}
                disabled={paginaAtual <= 1 || loading}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Anterior
              </button>
              <span className="text-sm text-gray-600">
                Pagina {paginaAtual} de {totalPaginas}
              </span>
              <button
                type="button"
                onClick={() =>
                  setPaginaAtual((prev) => Math.min(totalPaginas, prev + 1))
                }
                disabled={paginaAtual >= totalPaginas || loading}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Proxima
              </button>
            </div>
          )}
        </div>

        {loading ? (
          <div className="px-5 py-12 text-center text-sm text-gray-500">
            Carregando relatorio de valorizacao...
          </div>
        ) : dados.items.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm text-gray-500">
            Ajuste os filtros ou desmarque a opcao de estoque para ampliar a
            busca.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Produto
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Fornecedor
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Marca / Setor
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Estoque
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Custo un.
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Venda un.
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Total custo
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Total venda
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {dados.items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 align-top">
                      <div className="font-semibold text-gray-900">
                        {item.nome}
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        Codigo {item.codigo || "-"} {item.sku ? `| SKU ${item.sku}` : ""}
                      </div>
                      {item.categoria_nome && (
                        <div className="mt-1 text-xs text-gray-400">
                          Categoria: {item.categoria_nome}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 align-top text-sm text-gray-700">
                      {item.fornecedor_nome || "-"}
                    </td>
                    <td className="px-4 py-3 align-top text-sm text-gray-700">
                      <div>{item.marca_nome || "Sem marca"}</div>
                      <div className="mt-1 text-xs text-gray-500">
                        {item.departamento_nome || "Sem setor"}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                      {formatarQuantidade(item.estoque_atual)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-700">
                      {formatarMoeda(item.preco_custo)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-700">
                      {formatarMoeda(item.preco_venda)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-semibold text-blue-700">
                      {formatarMoeda(item.valor_custo_total)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-semibold text-emerald-700">
                      {formatarMoeda(item.valor_venda_total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
