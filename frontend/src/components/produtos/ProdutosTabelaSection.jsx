import { formatarData } from "../../api/produtos";
import ActionButton from "../ui/ActionButton";
import ChannelBadges from "../ui/ChannelBadges";
import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import PaginationControls from "../ui/PaginationControls";
import {
  montarTooltipLotesValidade,
  obterCanaisAtivosProduto,
  obterEstoqueVisualProduto,
  obterLotesValidadeDisponiveis,
} from "./produtosUtils";

function obterValidadeResumoProduto(produto) {
  const lotes = obterLotesValidadeDisponiveis(produto);
  const primeiroLoteComValidade = lotes.find((lote) => lote.data_validade);
  const validadeProxima =
    primeiroLoteComValidade?.data_validade ||
    produto?.validade_proxima_listagem ||
    produto?.validade_proxima;
  const tooltip = montarTooltipLotesValidade(lotes, formatarData);

  if (!validadeProxima) {
    return {
      data: "-",
      apoio: "Sem lote com validade",
      className: "text-gray-500",
      surfaceClassName: "bg-gray-50 border-gray-200",
      tooltip,
    };
  }

  const dataValidade = new Date(validadeProxima);
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  dataValidade.setHours(0, 0, 0, 0);
  const dias = Math.floor((dataValidade - hoje) / (1000 * 60 * 60 * 24));

  if (dias < 0) {
    return {
      data: formatarData(validadeProxima),
      apoio: `${Math.abs(dias)} dia(s) vencido`,
      className: "text-red-700",
      surfaceClassName: "bg-red-50 border-red-200",
      tooltip,
    };
  }

  if (dias <= 30) {
    return {
      data: formatarData(validadeProxima),
      apoio: `Vence em ${dias} dia(s)`,
      className: "text-orange-700",
      surfaceClassName: "bg-orange-50 border-orange-200",
      tooltip,
    };
  }

  if (dias <= 90) {
    return {
      data: formatarData(validadeProxima),
      apoio: `Vence em ${dias} dia(s)`,
      className: "text-yellow-700",
      surfaceClassName: "bg-yellow-50 border-yellow-200",
      tooltip,
    };
  }

  return {
    data: formatarData(validadeProxima),
    apoio: `Vence em ${dias} dia(s)`,
    className: "text-gray-700",
    surfaceClassName: "bg-gray-50 border-gray-200",
    tooltip,
  };
}

function obterImagemProduto(produto) {
  if (!produto?.imagem_principal) return null;
  return produto.imagem_principal.startsWith("http")
    ? produto.imagem_principal
    : `${window.location.origin}${produto.imagem_principal}`;
}

export default function ProdutosTabelaSection({
  colunasVisiveis,
  copiarTexto,
  editandoMargem,
  editandoPreco,
  getCorEstoque,
  getValidadeMaisProxima,
  handleCancelarEdicaoPreco,
  handleEditarPreco,
  handleExcluir,
  handleSalvarMargem,
  handleSalvarPreco,
  handleSelecionar,
  handleSelecionarTodos,
  handleToggleAtivo,
  isProdutoComComposicao,
  itensPorPagina,
  kitsExpandidos,
  linhaProdutoRefs,
  loading,
  navigate,
  novoPreco,
  onChangeItensPorPagina,
  onIrParaPagina,
  paginaAtual,
  paisExpandidos,
  produtos,
  selecionados,
  selecionadosCount,
  setEditandoMargem,
  setNovoPreco,
  toggleKitExpandido,
  togglePaiExpandido,
  totalItens,
  totalPaginas,
}) {
  const produtosValidos = produtos.filter((produto, idx) => {
    if (!produto || !produto.id) {
      console.error(`Produto invalido no indice ${idx}:`, produto);
      return false;
    }

    return true;
  });

  const produtoHeaderContext = {
    produtos: produtosValidos,
    selecionados,
    handleSelecionarTodos,
  };

  const getProdutoCellContext = () => ({
    selecionados,
    handleSelecionar,
    kitsExpandidos,
    toggleKitExpandido,
    paisExpandidos,
    togglePaiExpandido,
    copiarTexto,
    editandoMargem,
    setEditandoMargem,
    handleSalvarMargem,
    editandoPreco,
    novoPreco,
    setNovoPreco,
    handleSalvarPreco,
    handleCancelarEdicaoPreco,
    handleEditarPreco,
    getValidadeMaisProxima,
    getCorEstoque,
    navigate,
    handleExcluir,
    handleToggleAtivo,
  });

  const isProdutoExpandido = (produto) =>
    isProdutoComComposicao(produto) &&
    kitsExpandidos.includes(produto.id) &&
    produto.composicao_kit &&
    produto.composicao_kit.length > 0;

  const renderProdutoExpandido = (produto, _rowIndex, colSpan) => (
    <tr
      key={`kit-${produto.id}`}
      className="bg-amber-50/50 border-l-4 border-amber-400"
    >
      <td colSpan={colSpan} className="px-4 py-3">
        <div className="ml-12">
          <div className="text-xs font-semibold text-amber-800 mb-2 flex items-center gap-2">
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
            COMPOSICAO DO KIT:
          </div>
          <div className="grid gap-1">
            {produto.composicao_kit.map((componente, index) => (
              <div
                key={index}
                className="flex items-center gap-3 text-xs bg-white rounded px-3 py-2 border border-amber-200"
              >
                <span className="font-mono font-semibold text-amber-700 min-w-[40px]">
                  {componente.quantidade}x
                </span>
                <span className="flex-1 text-gray-700">
                  {componente.produto_nome ||
                    componente.nome ||
                    `Produto #${
                      componente.produto_id ||
                      componente.produto_componente_id
                    }`}
                </span>
                {componente.produto_estoque !== undefined && (
                  <span className="text-gray-500">
                    Estoque:{" "}
                    <span
                      className={
                        componente.produto_estoque > 0
                          ? "text-green-600 font-semibold"
                          : "text-red-600 font-semibold"
                      }
                    >
                      {componente.produto_estoque}
                    </span>
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </td>
    </tr>
  );

  return (
    <>
      <PaginationControls
        currentPage={paginaAtual}
        itemName="produtos"
        itemsPerPage={itensPorPagina}
        loading={loading}
        onItemsPerPageChange={onChangeItensPorPagina}
        onPageChange={onIrParaPagina}
        totalItems={totalItens}
        totalPages={totalPaginas}
        variant="top"
      />

      <div id="tour-produtos-lista" className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="md:hidden">
          {loading ? (
            <div className="px-4 py-8 text-center text-gray-500">
              Carregando produtos...
            </div>
          ) : produtos.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-500">
              Nenhum produto encontrado
            </div>
          ) : (
            <div className="space-y-3 bg-gray-50 p-3">
              {produtosValidos.map((produto) => {
                const validade = obterValidadeResumoProduto(produto);
                const estoqueAtual = obterEstoqueVisualProduto(produto);
                const reservado = Number(produto.estoque_reservado || 0);
                const estoqueDisponivel = Number((estoqueAtual - reservado).toFixed(2));
                const imagem = obterImagemProduto(produto);
                const codigo = produto.codigo || produto.sku || produto.codigo_barras;
                const canaisAtivos = obterCanaisAtivosProduto(produto);

                return (
                  <article
                    key={produto.id}
                    ref={(element) => {
                      linhaProdutoRefs.current[produto.id] = element;
                    }}
                    onClick={() => navigate(`/produtos/${produto.id}/editar`)}
                    className={`rounded-lg border bg-white p-3 shadow-sm ${
                      produto.ativo === false ? "border-slate-200 bg-slate-50 opacity-80" : "border-gray-200"
                    }`}
                  >
                    <div className="flex gap-3">
                      <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg border border-gray-200 bg-gray-100">
                        {imagem ? (
                          <img
                            src={imagem}
                            alt={produto.nome}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-xs text-gray-400">
                            Sem foto
                          </div>
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-start gap-2">
                          <input
                            type="checkbox"
                            checked={selecionados.includes(produto.id)}
                            onClick={(event) => event.stopPropagation()}
                            onChange={(event) => handleSelecionar(produto.id, event.nativeEvent)}
                            className="mt-1 h-4 w-4 rounded text-blue-600"
                          />
                          <div className="min-w-0 flex-1">
                            <h3 className="line-clamp-2 text-sm font-semibold text-gray-900">
                              {produto.nome}
                            </h3>
                            <div className="mt-1 flex flex-wrap gap-1 text-[11px] text-gray-500">
                              {codigo && (
                                <span className="max-w-full break-all rounded-full bg-gray-100 px-2 py-0.5">
                                  Cod: {codigo}
                                </span>
                              )}
                              {produto.marca?.nome || produto.marca_nome ? (
                                <span className="rounded-full bg-gray-100 px-2 py-0.5">
                                  {produto.marca?.nome || produto.marca_nome}
                                </span>
                              ) : null}
                              {produto.ativo === false && (
                                <span className="rounded-full bg-slate-200 px-2 py-0.5 text-slate-700">
                                  Inativo
                                </span>
                              )}
                              <ChannelBadges channels={canaisAtivos} layout="row" empty="" />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 flex gap-2">
                      <div
                        className={`min-w-0 flex-1 rounded-lg border p-2 ${validade.surfaceClassName}`}
                        title={validade.tooltip}
                      >
                        <p className="text-[10px] font-semibold uppercase text-gray-500">
                          Validade
                        </p>
                        <p className={`mt-1 text-sm font-bold ${validade.className}`}>
                          {validade.data}
                        </p>
                        <p className="mt-0.5 text-[11px] text-gray-500">
                          {validade.apoio}
                        </p>
                      </div>
                      <div className="min-w-0 flex-1 rounded-lg border border-gray-200 bg-gray-50 p-2">
                        <p className="text-[10px] font-semibold uppercase text-gray-500">
                          Estoque
                        </p>
                        <p className={`mt-1 text-sm font-bold ${getCorEstoque(produto)}`}>
                          {produto.controlar_estoque ? estoqueDisponivel : "-"}
                        </p>
                        {reservado > 0 && (
                          <p className="mt-0.5 text-[11px] text-yellow-700">
                            {reservado} reservado
                          </p>
                        )}
                      </div>
                      <div className="min-w-0 flex-1 rounded-lg border border-gray-200 bg-gray-50 p-2">
                        <p className="text-[10px] font-semibold uppercase text-gray-500">
                          Venda
                        </p>
                        <p className="mt-1 text-sm font-bold text-gray-900">
                          <MoneyCell value={produto.preco_venda} />
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 flex gap-2">
                      <ActionButton
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          navigate(`/produtos/${produto.id}/editar`);
                        }}
                        intent="edit"
                        tone="solid"
                        size="sm"
                        className="flex-1"
                      >
                        Editar
                      </ActionButton>
                      {codigo && (
                        <ActionButton
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            copiarTexto(codigo, "Codigo");
                          }}
                          intent="neutral"
                          tone="soft"
                          size="sm"
                        >
                          Copiar
                        </ActionButton>
                      )}
                      <ActionButton
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          handleToggleAtivo(produto);
                        }}
                        intent={produto.ativo === false ? "create" : "warning"}
                        tone="soft"
                        size="sm"
                      >
                        {produto.ativo === false ? "Ativar" : "Inativar"}
                      </ActionButton>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>

        <div className="hidden overflow-x-auto md:block">
          <DataTable
            columns={colunasVisiveis}
            data={produtosValidos}
            emptyMessage="Nenhum produto encontrado"
            getCellContext={getProdutoCellContext}
            getRowKey={(produto) => produto.id}
            getRowRef={(produto, _rowIndex, element) => {
              linhaProdutoRefs.current[produto.id] = element;
            }}
            headerContext={produtoHeaderContext}
            isRowExpanded={isProdutoExpandido}
            loading={loading}
            loadingMessage="Carregando produtos..."
            onRowClick={(produto, _rowIndex, event) => {
              if (!event.target.closest("button, input, a, svg")) {
                navigate(`/produtos/${produto.id}/editar`);
              }
            }}
            renderExpandedRow={renderProdutoExpandido}
            rowClassName={(produto) => {
              const isKit = isProdutoComComposicao(produto);
              return [
                "hover:bg-gray-50 transition-colors cursor-pointer",
                produto.ativo === false ? "bg-slate-100 opacity-70" : "",
                produto.tipo_produto === "VARIACAO" ? "bg-blue-50/30" : "",
                isKit ? "bg-amber-50/30" : "",
              ]
                .filter(Boolean)
                .join(" ");
            }}
            tableClassName="min-w-full divide-y divide-gray-200"
            tbodyClassName="bg-white divide-y divide-gray-200"
            theadClassName="bg-gray-50"
          />
        </div>

        <PaginationControls
          currentPage={paginaAtual}
          itemName="produtos"
          itemsPerPage={itensPorPagina}
          loading={loading}
          onItemsPerPageChange={onChangeItensPorPagina}
          onPageChange={onIrParaPagina}
          totalItems={totalItens}
          totalPages={totalPaginas}
          variant="bottom"
        />

        {!loading && selecionadosCount > 0 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
            <div className="flex justify-between items-center text-sm text-gray-600">
              <span>
                {selecionadosCount} produto{selecionadosCount > 1 ? "s" : ""} selecionado
                {selecionadosCount > 1 ? "s" : ""}
              </span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
