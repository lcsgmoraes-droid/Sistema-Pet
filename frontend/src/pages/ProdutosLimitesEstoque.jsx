import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import api from "../api";
import ActionButton from "../components/ui/ActionButton";
import FornecedorSelector, {
  getFornecedorNome,
} from "../components/fornecedores/FornecedorSelector";
import {
  CategoriaProdutoSelector,
  MarcaProdutoSelector,
} from "../components/produtos/CatalogoProdutoSelectors";
import useProdutosCatalogos from "../hooks/useProdutosCatalogos";
import {
  FILTROS_INICIAIS,
  SITUACOES_ESTOQUE,
  formatarQuantidade,
  montarPlanilhaLimites,
  parametrosLimites,
} from "./estoque-limites/estoqueLimitesUtils";

const ENDPOINT = "/produtos/relatorio/limites-estoque";
const campoClasse = "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm";

export default function ProdutosLimitesEstoque({ embedded = false }) {
  const Titulo = embedded ? "h2" : "h1";
  const [filtros, setFiltros] = useState(FILTROS_INICIAIS);
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [exportando, setExportando] = useState(false);
  const [erro, setErro] = useState("");
  const [atualizacao, setAtualizacao] = useState(0);
  const [fornecedorSelecionado, setFornecedorSelecionado] = useState(null);
  const [fornecedorBusca, setFornecedorBusca] = useState("");
  const { categorias, marcas, fornecedores } = useProdutosCatalogos();

  useEffect(() => {
    const controller = new AbortController();
    setCarregando(true);
    setErro("");
    const timer = setTimeout(async () => {
      try {
        const resposta = await api.get(ENDPOINT, {
          params: parametrosLimites(filtros),
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setDados(resposta.data);
      } catch (_error) {
        if (!controller.signal.aborted) {
          setDados(null);
          setErro("Não foi possível carregar o relatório. Tente atualizar novamente.");
        }
      } finally {
        if (!controller.signal.aborted) setCarregando(false);
      }
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [filtros, atualizacao]);

  const alterarFiltro = (chave, valor) => {
    setFiltros((anterior) => ({ ...anterior, [chave]: valor, page: 1 }));
  };

  const exportar = async () => {
    setExportando(true);
    try {
      const { data } = await api.get(ENDPOINT, {
        params: { ...parametrosLimites(filtros), page: 1, export_all: true },
      });
      if (!data.itens.length) {
        toast.error("Nenhum produto para exportar.");
        return;
      }
      const { default: writeExcelFile } = await import("write-excel-file/browser");
      await writeExcelFile(montarPlanilhaLimites(data.itens), {
        sheet: "Limites de estoque",
        stickyRowsCount: 1,
        columns: [42, 22, 25, 22, 32, 12, 18, 18, 18, 24, 24, 26].map((width) => ({ width })),
      }).toFile(`estoque_minimo_maximo_${new Date().toLocaleDateString("sv-SE")}.xlsx`);
      toast.success(`${formatarQuantidade(data.total)} produtos exportados.`);
    } catch (_error) {
      toast.error("Não foi possível exportar o relatório. Tente novamente.");
    } finally {
      setExportando(false);
    }
  };

  return (
    <div className={embedded ? "space-y-5" : "space-y-5 p-0 md:p-6"}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Titulo className="text-2xl font-bold text-gray-900">Estoque mínimo e máximo</Titulo>
          <p className="mt-1 text-sm text-gray-600">
            Veja o que precisa de reposição e o que está em excesso.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ActionButton
            icon={RefreshCw}
            loading={carregando}
            tone="soft"
            onClick={() => setAtualizacao((valor) => valor + 1)}
          >
            Atualizar
          </ActionButton>
          <ActionButton
            icon={Download}
            loading={exportando}
            disabled={carregando || !dados?.total}
            onClick={exportar}
          >
            Exportar Excel
          </ActionButton>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="text-sm text-gray-700">
            Produto, código ou EAN
            <input
              className={`${campoClasse} mt-1`}
              placeholder="Buscar produto..."
              value={filtros.busca}
              onChange={(event) => alterarFiltro("busca", event.target.value)}
            />
          </label>
          <div>
            <p className="mb-1 text-sm text-gray-700">Categoria</p>
            <CategoriaProdutoSelector
              categorias={categorias}
              value={filtros.categoria_id}
              onChange={(valor) => alterarFiltro("categoria_id", valor)}
              showLabel={false}
            />
          </div>
          <div>
            <p className="mb-1 text-sm text-gray-700">Marca</p>
            <MarcaProdutoSelector
              marcas={marcas}
              value={filtros.marca_id}
              onChange={(valor) => alterarFiltro("marca_id", valor)}
              showLabel={false}
            />
          </div>
          <div>
            <p className="mb-1 text-sm text-gray-700">Fornecedor</p>
            <FornecedorSelector
              fornecedores={fornecedores}
              fornecedorId={filtros.fornecedor_id}
              fornecedorSelecionado={fornecedorSelecionado}
              value={fornecedorBusca}
              showLabel={false}
              allowCreate={false}
              onInputChange={(termo) => {
                setFornecedorBusca(termo);
                if (filtros.fornecedor_id) {
                  setFornecedorSelecionado(null);
                  alterarFiltro("fornecedor_id", "");
                }
              }}
              onSelect={(fornecedor) => {
                setFornecedorSelecionado(fornecedor);
                setFornecedorBusca(getFornecedorNome(fornecedor));
                alterarFiltro("fornecedor_id", fornecedor?.id || "");
              }}
              onClear={() => {
                setFornecedorSelecionado(null);
                setFornecedorBusca("");
                alterarFiltro("fornecedor_id", "");
              }}
            />
          </div>
          <label className="text-sm text-gray-700">
            Situação dos limites
            <select
              className={`${campoClasse} mt-1`}
              value={filtros.situacao}
              onChange={(event) => alterarFiltro("situacao", event.target.value)}
            >
              {Object.entries(SITUACOES_ESTOQUE).map(([valor, { label }]) => (
                <option key={valor} value={valor}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-gray-700">
            Saldo
            <select
              className={`${campoClasse} mt-1`}
              value={filtros.saldo}
              onChange={(event) => alterarFiltro("saldo", event.target.value)}
            >
              <option value="todos">Todos os saldos</option>
              <option value="zerado">Zerado</option>
              <option value="negativo">Negativo</option>
              <option value="sem_estoque">Zerado ou negativo</option>
            </select>
          </label>
          <label className="text-sm text-gray-700">
            Cadastro
            <select
              className={`${campoClasse} mt-1`}
              value={filtros.ativo}
              onChange={(event) => alterarFiltro("ativo", event.target.value)}
            >
              <option value="ativos">Somente ativos</option>
              <option value="inativos">Somente inativos</option>
              <option value="todos">Ativos e inativos</option>
            </select>
          </label>
          <div className="flex items-end">
            <ActionButton
              tone="soft"
              onClick={() => {
                setFiltros(FILTROS_INICIAIS);
                setFornecedorSelecionado(null);
                setFornecedorBusca("");
              }}
            >
              Limpar filtros
            </ActionButton>
          </div>
        </div>
      </div>

      <div
        className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6"
        aria-label="Resumo por situação"
      >
        {Object.entries(SITUACOES_ESTOQUE)
          .filter(
            ([chave]) =>
              chave !== "limites_invalidos" ||
              dados?.resumo?.limites_invalidos ||
              filtros.situacao === chave,
          )
          .map(([chave, { label, cor }]) => (
            <button
              key={chave}
              type="button"
              aria-pressed={filtros.situacao === chave}
              onClick={() => alterarFiltro("situacao", chave)}
              className={`rounded-xl border p-4 text-left ${cor} ${filtros.situacao === chave ? "ring-2 ring-blue-500 ring-offset-2" : ""}`}
            >
              <span className="block text-sm">{label}</span>
              <strong className="mt-1 block text-2xl">
                {carregando || erro ? "—" : formatarQuantidade(dados?.resumo?.[chave] || 0)}
              </strong>
            </button>
          ))}
      </div>

      <div className="space-y-1 text-xs text-gray-600">
        <p>
          Comparação com o saldo atual, antes de descontar reservas. Inclui variações e kits
          físicos; serviços, produtos pai e kits virtuais não entram.
        </p>
        <p>
          Limites vazios ou zero aparecem como “—”. A falta é a quantidade para atingir o mínimo; o
          excesso é o que ultrapassa o máximo. Saldo igual ao máximo está dentro dos limites.
        </p>
        <p>
          Os indicadores contam todos os produtos dos filtros acima, independentemente da situação
          selecionada e da página. O Excel exporta todos os resultados da situação selecionada.
        </p>
      </div>

      {erro ? (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-800">
          {erro}
        </div>
      ) : (
        <div
          className="overflow-hidden rounded-xl border border-gray-200 bg-white"
          aria-busy={carregando}
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1050px] text-sm">
              <thead className="bg-gray-50 text-xs text-gray-600">
                <tr>
                  {[
                    "Produto / SKU",
                    "Fornecedor principal",
                    "Unidade",
                    "Saldo atual",
                    "Mínimo",
                    "Máximo",
                    "Situação",
                    "Falta até o mínimo",
                    "Excesso sobre o máximo",
                  ].map((titulo, indice) => (
                    <th
                      key={titulo}
                      scope="col"
                      className={`px-4 py-3 ${[3, 4, 5, 7, 8].includes(indice) ? "text-right" : "text-left"}`}
                    >
                      {titulo}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {carregando ? (
                  <tr>
                    <td colSpan={9} className="p-10 text-center text-gray-500" role="status">
                      Carregando relatório...
                    </td>
                  </tr>
                ) : !dados?.itens?.length ? (
                  <tr>
                    <td colSpan={9} className="p-10 text-center text-gray-500">
                      Nenhum produto encontrado com esses filtros.
                    </td>
                  </tr>
                ) : (
                  dados.itens.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50">
                      <td className="max-w-xs px-4 py-3">
                        <Link
                          to={`/produtos/${item.id}/movimentacoes`}
                          className="font-semibold text-blue-700 hover:underline"
                        >
                          {item.nome}
                        </Link>
                        <p className="text-xs text-gray-500">{item.codigo || "Sem código"}</p>
                        <p className="text-xs text-gray-500">
                          {[item.categoria, item.marca].filter(Boolean).join(" • ")}
                        </p>
                      </td>
                      <td className="max-w-[180px] px-4 py-3 text-gray-600">
                        {item.fornecedor || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{item.unidade}</td>
                      <td
                        className={`px-4 py-3 text-right font-semibold tabular-nums ${item.estoque_atual <= 0 ? "text-red-700" : "text-gray-900"}`}
                      >
                        {formatarQuantidade(item.estoque_atual)}
                        {item.estoque_atual <= 0 && (
                          <span className="block text-xs font-normal">
                            {item.estoque_atual < 0 ? "Negativo" : "Zerado"}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatarQuantidade(item.estoque_minimo)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatarQuantidade(item.estoque_maximo)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block whitespace-nowrap rounded-full border px-2 py-1 text-xs ${SITUACOES_ESTOQUE[item.situacao].cor}`}
                        >
                          {SITUACOES_ESTOQUE[item.situacao].label}
                        </span>
                        {item.situacao === "limites_invalidos" && (
                          <p className="mt-1 text-xs text-gray-500">
                            Há limite negativo ou máximo menor que mínimo.
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-medium tabular-nums text-red-700">
                        {formatarQuantidade(item.falta_minimo)}
                      </td>
                      <td className="px-4 py-3 text-right font-medium tabular-nums text-blue-700">
                        {formatarQuantidade(item.excesso_maximo)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-200 px-4 py-3 text-sm text-gray-600">
            <p>
              {carregando
                ? "Carregando..."
                : `${formatarQuantidade(dados?.total || 0)} produtos • Página ${formatarQuantidade(filtros.page)} de ${formatarQuantidade(Math.max(dados?.total_pages || 0, 1))}`}
            </p>
            <div className="flex items-center gap-2">
              <select
                aria-label="Produtos por página"
                className="rounded-lg border border-gray-300 px-2 py-1"
                value={filtros.page_size}
                onChange={(event) => alterarFiltro("page_size", Number(event.target.value))}
              >
                {[25, 50, 100, 200].map((tamanho) => (
                  <option key={tamanho} value={tamanho}>
                    {tamanho} por página
                  </option>
                ))}
              </select>
              <ActionButton
                tone="soft"
                disabled={carregando || filtros.page <= 1}
                onClick={() => setFiltros((anterior) => ({ ...anterior, page: anterior.page - 1 }))}
              >
                Anterior
              </ActionButton>
              <ActionButton
                tone="soft"
                disabled={carregando || filtros.page >= (dados?.total_pages || 0)}
                onClick={() => setFiltros((anterior) => ({ ...anterior, page: anterior.page + 1 }))}
              >
                Próxima
              </ActionButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
