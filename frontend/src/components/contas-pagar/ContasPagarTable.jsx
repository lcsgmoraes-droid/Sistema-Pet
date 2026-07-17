import { Ban, Edit3, RotateCcw, Trash2, Wallet } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import FornecedorIdentity, { getFornecedorIdentityName } from "../ui/FornecedorIdentity";
import { ehVencimentoHojeContasPagar } from "./contasPagarHelpers";

export default function ContasPagarTable({
  contasVisiveis,
  contasSelecionadas,
  todasVisiveisSelecionadas,
  algumasVisiveisSelecionadas,
  selecionarTodasContasVisiveis,
  alternarSelecaoConta,
  getContaTooltip,
  getDescricaoPrincipal,
  getStatusBadge,
  formatarData,
  abrirModalEdicao,
  abrirModalPagamento,
  precisaClassificacao,
  abrirModalClassificacao,
  excluirContaPagar,
  contaTemPagamento,
  totalSelecionadas,
  abrirPagamentoEmLote,
  editarContaSelecionada,
  estornarContasSelecionadas,
  cancelarContasSelecionadas,
  excluirContasSelecionadas,
  limparSelecaoContas,
  haContaPagavelSelecionada,
  haContaPagaSelecionada,
  haContaCancelavelSelecionada,
  haContaExcluivelSelecionada,
}) {
  const contasPagarColumns = [
    {
      key: "selecao",
      headerClassName: "w-[44px] text-center",
      className: "w-[44px] text-center",
      renderHeader: () => (
        <input
          aria-checked={
            todasVisiveisSelecionadas ? "true" : algumasVisiveisSelecionadas ? "mixed" : "false"
          }
          aria-label="Selecionar todos os lancamentos visiveis"
          checked={todasVisiveisSelecionadas}
          className="contas-pagar-select-all h-4 w-4 rounded border-slate-300"
          onChange={selecionarTodasContasVisiveis}
          type="checkbox"
        />
      ),
      render: (conta) => (
        <input
          aria-label={`Selecionar lancamento ${conta.id}`}
          checked={contasSelecionadas.includes(conta.id)}
          className="contas-pagar-select-row h-4 w-4 rounded border-slate-300"
          onChange={() => alternarSelecaoConta(conta.id)}
          onClick={(event) => event.stopPropagation()}
          type="checkbox"
        />
      ),
    },
    {
      key: "id",
      header: "ID",
      render: (conta) => conta.id,
    },
    {
      key: "descricao",
      header: "Conta",
      className: "w-[210px] max-w-[210px]",
      cellStyle: { width: 210, maxWidth: 210 },
      render: (conta) => (
        <div className="min-w-0 max-w-[210px]" title={getContaTooltip(conta)}>
          <div
            className="truncate text-sm font-semibold text-slate-900"
            title={getContaTooltip(conta)}
          >
            {getDescricaoPrincipal(conta)}
          </div>
          <div className="mt-1 flex flex-nowrap gap-1 overflow-hidden">
            {conta.eh_parcelado && (
              <span className="shrink-0 px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-700">
                {conta.numero_parcela}/{conta.total_parcelas}
              </span>
            )}
            {conta.e_custo_fixo === true && (
              <span className="shrink-0 px-2 py-0.5 text-xs rounded-full bg-orange-100 text-orange-700 font-semibold">
                Fixo
              </span>
            )}
            {conta.e_custo_fixo === false && (
              <span className="shrink-0 px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700 font-semibold">
                Variavel
              </span>
            )}
          </div>
        </div>
      ),
    },
    {
      key: "fornecedor",
      header: "Fornecedor",
      className: "w-[220px] max-w-[220px]",
      cellStyle: { width: 220, maxWidth: 220 },
      render: (conta) => {
        const fornecedorNome = getFornecedorIdentityName(conta);
        return (
          <div className="max-w-[220px] truncate" title={fornecedorNome}>
            <FornecedorIdentity
              className="w-full max-w-[220px] truncate"
              copyable={false}
              fallback=""
              nameClassName="max-w-[220px] truncate font-medium text-slate-700"
              record={conta}
              showDocument={false}
            />
          </div>
        );
      },
    },
    {
      key: "tipo",
      header: "Tipo",
      render: (conta) =>
        conta.tipo_despesa_nome ? (
          <span
            className="inline-flex max-w-[150px] truncate px-2 py-1 text-xs rounded-full bg-slate-100 text-slate-700"
            title={conta.tipo_despesa_nome}
          >
            {conta.tipo_despesa_nome}
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        ),
    },
    {
      key: "vencimento",
      header: "Vencimento",
      headerClassName: "w-[110px] whitespace-nowrap",
      className: "w-[110px] whitespace-nowrap",
      render: (conta) => (
        <div className="flex flex-col items-start gap-1">
          <span>{formatarData(conta.data_vencimento)}</span>
          {ehVencimentoHojeContasPagar(conta.data_vencimento) && (
            <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold leading-none text-amber-800">
              Hoje
            </span>
          )}
        </div>
      ),
    },
    {
      key: "valor_original",
      header: "Original",
      title: "Valor original",
      align: "right",
      headerClassName: "w-[110px] whitespace-nowrap",
      className: "w-[110px] whitespace-nowrap tabular-nums",
      render: (conta) => <MoneyCell value={conta.valor_original} />,
    },
    {
      key: "valor_pago",
      header: "Pago",
      title: "Valor pago",
      align: "right",
      headerClassName: "w-[100px] whitespace-nowrap",
      className: "w-[100px] whitespace-nowrap tabular-nums",
      render: (conta) => <MoneyCell value={conta.valor_pago} zeroAsDash />,
    },
    {
      key: "saldo",
      header: "Saldo",
      align: "right",
      headerClassName: "w-[100px] whitespace-nowrap",
      className: "w-[100px] whitespace-nowrap tabular-nums font-bold",
      render: (conta) => <MoneyCell value={conta.valor_final - conta.valor_pago} zeroAsDash />,
    },
    {
      key: "status",
      header: "Status",
      render: getStatusBadge,
    },
    {
      key: "acoes",
      header: "Acoes",
      headerClassName:
        "contas-pagar-actions-cell sticky right-0 z-20 w-[260px] min-w-[260px] bg-gray-50 text-right",
      className:
        "contas-pagar-actions-cell sticky right-0 z-10 w-[260px] min-w-[260px] border-l border-slate-100 bg-white",
      render: (conta) => (
        <div className="flex flex-wrap items-center justify-end gap-2">
          <ActionButton
            intent="edit"
            tone="soft"
            size="xs"
            icon={Edit3}
            onClick={() => abrirModalEdicao(conta)}
            title="Editar conta a pagar"
          >
            Editar
          </ActionButton>
          {conta.status !== "pago" && (
            <ActionButton
              intent="create"
              size="xs"
              onClick={() => abrirModalPagamento(conta)}
              title="Registrar Pagamento"
            >
              Pagar
            </ActionButton>
          )}
          {precisaClassificacao(conta) && (
            <ActionButton
              intent="warning"
              size="xs"
              onClick={() => abrirModalClassificacao(conta)}
              title="Classificar categoria, DRE e tipo da despesa"
            >
              Classificar
            </ActionButton>
          )}
          <ActionButton
            intent="delete"
            tone="soft"
            size="xs"
            icon={Trash2}
            onClick={() => excluirContaPagar(conta)}
            disabled={contaTemPagamento(conta)}
            title="Excluir conta sem pagamento"
          >
            Excluir
          </ActionButton>
        </div>
      ),
    },
  ];

  return (
    <>
      {/* Tabela de Contas */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {totalSelecionadas > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3">
            <div>
              <div className="text-sm font-semibold text-slate-800">Acoes em lote</div>
              <div className="text-xs text-slate-500">
                {totalSelecionadas} lancamento(s) selecionado(s)
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <ActionButton
                intent="create"
                size="xs"
                icon={Wallet}
                disabled={!haContaPagavelSelecionada}
                onClick={abrirPagamentoEmLote}
                title="Baixar em lote os lancamentos selecionados com saldo aberto"
                type="button"
              >
                Pagar selecionados
              </ActionButton>
              <ActionButton
                intent="edit"
                tone="soft"
                size="xs"
                icon={Edit3}
                disabled={totalSelecionadas !== 1}
                onClick={editarContaSelecionada}
                title="Editar apenas um lancamento selecionado"
                type="button"
              >
                Editar selecionado
              </ActionButton>
              <ActionButton
                intent="warning"
                tone="soft"
                size="xs"
                icon={RotateCcw}
                disabled={!haContaPagaSelecionada}
                onClick={estornarContasSelecionadas}
                title="Estornar pagamentos selecionados"
                type="button"
              >
                Estornar pagamento
              </ActionButton>
              <ActionButton
                intent="warning"
                tone="soft"
                size="xs"
                icon={Ban}
                disabled={!haContaCancelavelSelecionada}
                onClick={cancelarContasSelecionadas}
                title="Cancelar lancamentos sem apagar historico"
                type="button"
              >
                Cancelar lancamento
              </ActionButton>
              <ActionButton
                intent="delete"
                tone="soft"
                size="xs"
                icon={Trash2}
                disabled={!haContaExcluivelSelecionada}
                onClick={excluirContasSelecionadas}
                title="Excluir lancamentos sem pagamento"
                type="button"
              >
                Excluir selecionados
              </ActionButton>
              <ActionButton
                intent="neutral"
                tone="soft"
                size="xs"
                onClick={limparSelecaoContas}
                type="button"
              >
                Limpar selecao
              </ActionButton>
            </div>
          </div>
        )}
        <DataTable
          columns={contasPagarColumns}
          data={contasVisiveis}
          emptyMessage="Nenhuma conta encontrada"
          getRowKey={(conta) => conta.id}
          tableClassName="min-w-[1280px]"
          theadClassName="bg-gray-50"
          tbodyClassName="divide-y divide-gray-200"
        />

        {contasVisiveis.length > 0 && (
          <div className="bg-green-50 border-t border-green-200 px-4 py-3">
            <strong>Total:</strong> {contasVisiveis.length} conta(s) |
            <strong className="ml-3">Saldo a Pagar:</strong>{" "}
            <MoneyCell
              value={contasVisiveis.reduce((sum, c) => sum + (c.valor_final - c.valor_pago), 0)}
              zeroAsDash
            />
          </div>
        )}
      </div>
    </>
  );
}
