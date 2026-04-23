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
  categoria_id: "",
  fornecedor_id: "",
  marca_id: "",
  departamento_id: "",
  apenas_com_estoque: true,
  incluir_kits_virtuais: false,
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
    slate: "border-slate-200 bg-slate-50 text-slate-900",
  };

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${estilos[destaque] || estilos.blue}`}>
      <p className="text-sm font-medium opacity-80">{titulo}</p>
      <p className="mt-2 text-2xl font-bold">{valor}</p>
      <p className="mt-2 text-xs opacity-75">{descricao}</p>
    </div>
  );
}

function BadgeTipoProduto({ item }) {
  if (item.tipo_kit === "FISICO") {
    return (
      <span className="inline-flex rounded-full bg-sky-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-sky-700">
        Kit fisico
      </span>
    );
  }

  if (item.tipo_kit === "VIRTUAL") {
    return (
      <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
        Kit virtual
      </span>
    );
  }

  if (item.tipo_produto === "VARIACAO") {
    return (
      <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-700">
        Variacao
      </span>
    );
  }

  return null;
}

function calcularPercentualReserva(estoqueTotal, estoqueDisponivel) {
  const total = Number(estoqueTotal || 0);
  if (total <= 0) return 0;
  const reservado = Math.max(total - Number(estoqueDisponivel || 0), 0);
  return Math.min((reservado / total) * 100, 100);
}

function BadgeSituacaoEstoque({ item }) {
  const estoqueAtual = Number(item.estoque_atual || 0);
  const estoqueDisponivel = Number(item.estoque_disponivel || 0);
  const percentualReserva = calcularPercentualReserva(estoqueAtual, estoqueDisponivel);

  if (estoqueDisponivel <= 0 && estoqueAtual > 0) {
    return (
      <span className="inline-flex rounded-full bg-rose-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-rose-700">
        Todo reservado
      </span>
    );
  }

  if (estoqueAtual <= 0) {
    return (
      <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-700">
        Sem estoque
      </span>
    );
  }

  if (percentualReserva >= 50) {
    return (
      <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
        Reserva alta
      </span>
    );
  }

  if (percentualReserva > 0) {
    return (
      <span className="inline-flex rounded-full bg-blue-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-700">
        Reserva parcial
      </span>
    );
  }

  return (
    <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-700">
      Livre
    </span>
  );
}

export default function ProdutosValorizacaoEstoque() {
  const navigate = useNavigate();
  const { categorias, fornecedores, marcas, departamentos } = useProdutosCatalogos();

  const [loading, setLoading] = useState(false);
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [filtrosForm, setFiltrosForm] = useState(filtrosIniciais);
  const [filtrosAplicados, setFiltrosAplicados] = useState(filtrosIniciais);
  const [dados, setDados] = useState({
    items: [],
    areas: [],
    total: 0,
    page: 1,
    page_size: ITENS_POR_PAGINA_INICIAL,
    pages: 0,
    totais: {
      total_produtos: 0,
      total_itens_estoque: 0,
      total_itens_reservados: 0,
      total_itens_disponiveis: 0,
      valor_custo_total: 0,
      valor_venda_total: 0,
      margem_potencial_total: 0,
      total_areas: 0,
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
        incluir_kits_virtuais: filtros.incluir_kits_virtuais,
      };

      if (filtros.busca.trim()) params.busca = filtros.busca.trim();
      if (filtros.categoria_id) params.categoria_id = filtros.categoria_id;
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
      setDados({
        items: [],
        areas: [],
        total: 0,
        page: 1,
        page_size: ITENS_POR_PAGINA_INICIAL,
        pages: 0,
        totais: {
          total_produtos: 0,
          total_itens_estoque: 0,
          total_itens_reservados: 0,
          total_itens_disponiveis: 0,
          valor_custo_total: 0,
          valor_venda_total: 0,
          margem_potencial_total: 0,
          total_areas: 0,
        },
      });
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
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Valorizacao de Estoque
          </h1>
          <p className="mt-2 max-w-4xl text-sm text-gray-600">
            Use esta tela para medir o estoque fisico por area, produto e total,
            olhando custo, potencial de venda e saldo disponivel. Kits virtuais
            ficam fora da conta por padrao para nao duplicar o mesmo estoque dos
            itens base.
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
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
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
              Categoria
            </label>
            <select
              value={filtrosForm.categoria_id}
              onChange={(event) =>
                atualizarFiltro("categoria_id", event.target.value)
              }
              className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">Todas as categorias</option>
              {categorias.map((categoria) => (
                <option key={categoria.id} value={categoria.id}>
                  {categoria.nome}
                </option>
              ))}
            </select>
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
              Area / setor
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

        <div className="mt-4 flex flex-col gap-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center">
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

              <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={filtrosForm.incluir_kits_virtuais}
                  onChange={(event) =>
                    atualizarFiltro("incluir_kits_virtuais", event.target.checked)
                  }
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                Incluir kits virtuais
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

          <div
            className={`rounded-2xl border px-4 py-3 text-sm ${
              filtrosAplicados.incluir_kits_virtuais
                ? "border-amber-200 bg-amber-50 text-amber-900"
                : "border-emerald-200 bg-emerald-50 text-emerald-900"
            }`}
          >
            {filtrosAplicados.incluir_kits_virtuais
              ? "Os kits virtuais entraram nesta conta. Eles podem duplicar o mesmo estoque dos itens base."
              : "Os kits virtuais estao fora da valorizacao por padrao. Assim o total reflete o estoque fisico real."}
          </div>
        </div>
      </form>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
        <ResumoCard
          titulo="Valor em custo"
          valor={formatarMoeda(dados.totais.valor_custo_total)}
          descricao="Total investido no estoque filtrado."
          destaque="blue"
        />
        <ResumoCard
          titulo="Valor em venda"
          valor={formatarMoeda(dados.totais.valor_venda_total)}
          descricao="Potencial bruto de venda do estoque filtrado."
          destaque="emerald"
        />
        <ResumoCard
          titulo="Margem potencial"
          valor={formatarMoeda(dados.totais.margem_potencial_total)}
          descricao="Diferenca entre preco de venda e custo total."
          destaque="amber"
        />
        <ResumoCard
          titulo="Itens reservados"
          valor={formatarQuantidade(dados.totais.total_itens_reservados)}
          descricao="Quantidade comprometida em reservas e pedidos em aberto."
          destaque="amber"
        />
        <ResumoCard
          titulo="Estoque disponivel"
          valor={formatarQuantidade(dados.totais.total_itens_disponiveis)}
          descricao="Saldo livre para venda imediata e novas transferencias."
          destaque="violet"
        />
        <ResumoCard
          titulo="Areas no filtro"
          valor={String(dados.totais.total_areas || 0)}
          descricao={`${dados.totais.total_produtos || 0} produto(s) considerados no estoque fisico.`}
          destaque="slate"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <section className="rounded-2xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-200 px-5 py-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Resumo por area
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Veja quanto cada area representa em unidades, custo e potencial de venda.
            </p>
          </div>

          {loading ? (
            <div className="px-5 py-10 text-center text-sm text-gray-500">
              Calculando areas...
            </div>
          ) : dados.areas.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-gray-500">
              Nenhuma area encontrada para os filtros atuais.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Area
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Estoque
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Disponivel
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Reserva %
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Custo
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {dados.areas.map((area) => {
                    const percentualReserva = calcularPercentualReserva(
                      area.total_itens_estoque,
                      area.total_itens_disponiveis,
                    );

                    return (
                    <tr key={area.area_nome} className="hover:bg-gray-50">
                      <td className="px-4 py-3 align-top">
                        <div className="font-semibold text-gray-900">
                          {area.area_nome}
                        </div>
                        <div className="mt-1 text-xs text-gray-500">
                          {area.total_produtos} produto(s)
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-gray-700">
                        {formatarQuantidade(area.total_itens_estoque)}
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-gray-700">
                        {formatarQuantidade(area.total_itens_disponiveis)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex min-w-[76px] flex-col items-end gap-1">
                          <span className="text-sm font-semibold text-slate-800">
                            {percentualReserva.toFixed(1)}%
                          </span>
                          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                            <div
                              className={`h-full ${
                                percentualReserva >= 50
                                  ? "bg-amber-400"
                                  : percentualReserva > 0
                                    ? "bg-blue-400"
                                    : "bg-emerald-400"
                              }`}
                              style={{ width: `${percentualReserva}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-sm font-semibold text-blue-700">
                        {formatarMoeda(area.valor_custo_total)}
                        <div className="mt-1 text-xs font-normal text-emerald-700">
                          Venda: {formatarMoeda(area.valor_venda_total)}
                        </div>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-gray-200 bg-white shadow-sm">
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
              Ajuste os filtros ou desmarque a opcao de estoque para ampliar a busca.
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
                      Marca / area
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Estoque
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Reservado
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Disponivel
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Situacao
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
                  {dados.items.map((item) => {
                    const percentualReserva = calcularPercentualReserva(
                      item.estoque_atual,
                      item.estoque_disponivel,
                    );

                    return (
                    <tr key={item.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 align-top">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-gray-900">
                            {item.nome}
                          </span>
                          <BadgeTipoProduto item={item} />
                          <BadgeSituacaoEstoque item={item} />
                        </div>
                        <div className="mt-1 text-xs text-gray-500">
                          Codigo {item.codigo || "-"}
                          {item.sku ? ` | SKU ${item.sku}` : ""}
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
                      <td className="px-4 py-3 text-right text-sm text-amber-700">
                        {formatarQuantidade(item.estoque_reservado)}
                      </td>
                      <td className="px-4 py-3 text-right text-sm font-semibold text-emerald-700">
                        {formatarQuantidade(item.estoque_disponivel)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="inline-flex min-w-[84px] flex-col items-center gap-1">
                          <span className="text-xs font-semibold text-slate-700">
                            {percentualReserva.toFixed(1)}% reservado
                          </span>
                          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                            <div
                              className={`h-full ${
                                percentualReserva >= 50
                                  ? "bg-amber-400"
                                  : percentualReserva > 0
                                    ? "bg-blue-400"
                                    : "bg-emerald-400"
                              }`}
                              style={{ width: `${percentualReserva}%` }}
                            />
                          </div>
                        </div>
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
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
