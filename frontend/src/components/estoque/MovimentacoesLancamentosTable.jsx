import { Trash2 } from "lucide-react";
import { formatMoneyBRL } from "../../utils/formatters";
import ActionButton from "../ui/ActionButton";
import PaginationControls from "../ui/PaginationControls";
import StatusBadge from "../ui/StatusBadge";

const CANAL_CLASSES = {
  loja_fisica: "bg-emerald-100 text-emerald-700",
  mercado_livre: "bg-yellow-100 text-yellow-700",
  shopee: "bg-orange-100 text-orange-700",
  amazon: "bg-sky-100 text-sky-700",
  site: "bg-indigo-100 text-indigo-700",
  instagram: "bg-pink-100 text-pink-700",
  whatsapp: "bg-green-100 text-green-700",
};

const formatMoney = (valor) =>
  valor === null || valor === undefined ? "-" : formatMoneyBRL(valor);

function CustoCell({ movimentacao }) {
  const custo = movimentacao.custo_unitario;
  const variacao = movimentacao.variacao_custo;

  if (!custo) {
    return "-";
  }

  if (!variacao) {
    return <span className="text-slate-900">{formatMoney(custo)}</span>;
  }

  const tipoVariacao =
    variacao.tipo === "aumento"
      ? "text-red-600"
      : variacao.tipo === "reducao"
        ? "text-green-600"
        : "text-slate-900";
  const resumoVariacao = `${variacao.tipo === "aumento" ? "Aumento" : "Reducao"} de ${formatMoney(
    Math.abs(Number(variacao.diferenca_valor || 0)),
  )} (${Number(variacao.diferenca_percentual || 0).toFixed(1)}%)`;

  return (
    <div
      className="group relative inline-block"
      title={`Custo anterior: ${formatMoney(variacao.custo_anterior)}\nCusto atual: ${formatMoney(
        variacao.custo_atual,
      )}\n${resumoVariacao}`}
    >
      <span className={`font-semibold ${tipoVariacao}`}>{formatMoney(custo)}</span>

      <div className="absolute bottom-full left-1/2 z-50 mb-2 hidden -translate-x-1/2 transform group-hover:block">
        <div className="whitespace-nowrap rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
          <div className="mb-1 font-semibold">Variacao de custo</div>
          <div className="space-y-1">
            <div>Anterior: {formatMoney(variacao.custo_anterior)}</div>
            <div>Atual: {formatMoney(variacao.custo_atual)}</div>
            <div className={variacao.tipo === "aumento" ? "text-red-300" : "text-green-300"}>
              {resumoVariacao}
            </div>
          </div>
          <div className="absolute left-1/2 top-full -translate-x-1/2 transform">
            <div className="border-4 border-transparent border-t-slate-900" />
          </div>
        </div>
      </div>
    </div>
  );
}

function LoteCell({ movimentacao }) {
  if (movimentacao.lote_info) {
    return (
      <div className="flex flex-col">
        <span className="font-medium">{movimentacao.lote_info.nome}</span>
        {movimentacao.lote_info.consumido_acumulado !== undefined ? (
          <span className="text-xs text-slate-500">
            ({Number(movimentacao.lote_info.consumido_acumulado || 0).toFixed(0)}/
            {Number(movimentacao.lote_info.total_lote || 0).toFixed(0)})
          </span>
        ) : null}
      </div>
    );
  }

  return movimentacao.lote_nome || "-";
}

function CanalBadge({ labelsCanais, movimentacao }) {
  if (!movimentacao.canal) {
    return "-";
  }

  const canalClass = CANAL_CLASSES[movimentacao.canal] || "bg-slate-100 text-slate-600";

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${canalClass}`}
    >
      {movimentacao.canal_label || labelsCanais[movimentacao.canal] || movimentacao.canal}
    </span>
  );
}

export default function MovimentacoesLancamentosTable({
  abrirModal,
  formatarData,
  formatarQuantidade,
  getMotivoLabel,
  getOrigem,
  getSaldoAposLancamento,
  handleDelete,
  handleSelectAll,
  handleSelectOne,
  labelsCanais = {},
  loading = false,
  movimentacoes = [],
  movimentacoesPorPagina = 50,
  navigate,
  onItemsPerPageChange,
  onPageChange,
  paginaAtual = 1,
  paginasTotal = 0,
  produto,
  selectedIds = [],
  totalMovimentacoes = 0,
}) {
  const unidadeProduto = produto?.unidade || produto?.unidade_medida || "UN";

  return (
    <div className="overflow-hidden rounded-lg bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Lancamentos</h2>
          <p className="text-xs text-slate-500">
            {loading ? "Atualizando pagina..." : `${totalMovimentacoes} registro(s) no historico`}
          </p>
        </div>

        {selectedIds.length > 0 ? (
          <ActionButton icon={Trash2} intent="delete" onClick={handleDelete}>
            Excluir ({selectedIds.length})
          </ActionButton>
        ) : null}
      </div>

      <div className="overflow-x-auto">
        <table
          className={`min-w-full divide-y divide-slate-200 transition-opacity ${
            loading ? "opacity-50" : "opacity-100"
          }`}
        >
          <thead className="bg-slate-50">
            <tr>
              <th className="w-12 px-4 py-3">
                <input
                  type="checkbox"
                  checked={selectedIds.length === movimentacoes.length && movimentacoes.length > 0}
                  onChange={handleSelectAll}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                Data e hora
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-slate-500">
                Entrada
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-slate-500">
                Saida
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-slate-500">
                Saldo apos
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">
                Preco venda
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">
                Preco compra
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                Lote
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                Origem
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                Canal
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                Observacao
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {movimentacoes.length === 0 ? (
              <tr>
                <td colSpan="11" className="px-6 py-8 text-center text-slate-500">
                  Nenhuma movimentacao registrada
                </td>
              </tr>
            ) : (
              movimentacoes.map((movimentacao, index) => {
                const origem = getOrigem(movimentacao);
                const movCancelado = movimentacao.status === "cancelado";
                const saldoAposLancamento = getSaldoAposLancamento(movimentacao);
                const movAnterior = index > 0 ? movimentacoes[index - 1] : null;
                const mesmaVenda =
                  movAnterior &&
                  movimentacao.referencia_tipo === "venda" &&
                  movAnterior.referencia_tipo === "venda" &&
                  movimentacao.referencia_id === movAnterior.referencia_id;

                return (
                  <tr
                    key={movimentacao.id}
                    className={`cursor-pointer ${
                      movCancelado
                        ? "bg-slate-50/80 opacity-70 hover:bg-slate-100"
                        : "hover:bg-slate-50"
                    } ${mesmaVenda ? "border-l-4 border-l-blue-500 bg-blue-50" : ""}`}
                    onClick={() => abrirModal(movimentacao.tipo, movimentacao)}
                  >
                    <td className="w-12 px-4 py-3" onClick={(event) => event.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(movimentacao.id)}
                        onChange={() => handleSelectOne(movimentacao.id)}
                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-900">
                      {formatarData(movimentacao.created_at)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-center text-sm">
                      {movimentacao.tipo === "entrada" ? (
                        <span className="font-semibold text-green-600">
                          {Number(movimentacao.quantidade || 0).toFixed(2)}
                        </span>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-center text-sm">
                      {movimentacao.tipo === "saida" ? (
                        <span className="font-semibold text-red-600">
                          {Number(movimentacao.quantidade || 0).toFixed(2)}
                        </span>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-center text-sm">
                      {saldoAposLancamento !== null ? (
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">
                          {formatarQuantidade(saldoAposLancamento)} {unidadeProduto}
                        </span>
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-slate-900">
                      {formatMoney(movimentacao.preco_venda_unitario)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                      <CustoCell movimentacao={movimentacao} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
                      <LoteCell movimentacao={movimentacao} />
                    </td>
                    <td
                      className="whitespace-nowrap px-4 py-3 text-sm"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <div className="flex items-center gap-2">
                        {mesmaVenda ? (
                          <span
                            className="text-xs font-semibold text-blue-600"
                            title="Mesmo pedido/venda"
                          >
                            mesma venda
                          </span>
                        ) : null}
                        {origem.link ? (
                          <a
                            href={origem.link}
                            onClick={(event) => {
                              event.preventDefault();
                              event.stopPropagation();
                              navigate(origem.link);
                            }}
                            className={`${origem.cor} cursor-pointer font-medium hover:underline`}
                          >
                            {origem.texto}
                          </a>
                        ) : (
                          <span className={`${origem.cor} font-medium`}>{origem.texto}</span>
                        )}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm">
                      <CanalBadge labelsCanais={labelsCanais} movimentacao={movimentacao} />
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      <div className="flex items-center gap-2">
                        {movCancelado ? <StatusBadge status="cancelado" /> : null}
                        {movimentacao.motivo &&
                        movimentacao.motivo !== "compra" &&
                        !String(movimentacao.motivo).startsWith("venda") ? (
                          <StatusBadge intent="info">
                            {getMotivoLabel(movimentacao.motivo)}
                          </StatusBadge>
                        ) : null}
                        {movimentacao.observacao_exibicao || movimentacao.observacao}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      <PaginationControls
        currentPage={paginaAtual}
        disabled={loading}
        itemName="lancamentos"
        itemsPerPage={movimentacoesPorPagina}
        onItemsPerPageChange={onItemsPerPageChange}
        onPageChange={onPageChange}
        pageSizeOptions={[25, 50, 100]}
        totalItems={totalMovimentacoes}
        totalPages={paginasTotal}
        variant="bottom"
      />
    </div>
  );
}
