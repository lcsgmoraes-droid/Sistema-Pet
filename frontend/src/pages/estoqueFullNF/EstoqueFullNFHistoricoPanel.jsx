import { Edit3, RefreshCw } from "lucide-react";
import ActionButton from "../../components/ui/ActionButton";
import { ChannelBadge } from "../../components/ui/ChannelBadges";
import DataTable from "../../components/ui/DataTable";
import EmptyState from "../../components/ui/EmptyState";
import Panel from "../../components/ui/Panel";
import { formatMoneyBRL } from "../../utils/formatters";
import { contarBaixas, contarLancamentosFinanceiros, formatarDataHora } from "./estoqueFullNFUtils";

export default function EstoqueFullNFHistoricoPanel({ controller }) {
  const { carregandoHistorico, historico, carregarHistorico, abrirModalEditarCanal } = controller;

  return (
    <Panel
      className="space-y-4"
      title="Historico de baixas FULL"
      subtitle="Lancamentos processados por NF, com canal, estoque e tarifa financeira quando houver."
      actions={
        <ActionButton
          icon={RefreshCw}
          loading={carregandoHistorico}
          onClick={carregarHistorico}
          tone="soft"
        >
          Atualizar historico
        </ActionButton>
      }
    >
      {!carregandoHistorico && !historico.length && (
        <EmptyState title="Nenhuma baixa FULL por NF encontrada ainda." />
      )}

      <div className="space-y-3">
        {historico.map((lancamento) => (
          <div
            key={lancamento.numero_nf}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-base font-semibold text-slate-900">
                    NF {lancamento.numero_nf}
                  </h4>
                  <ChannelBadge
                    channel={lancamento.plataforma}
                    label={lancamento.plataforma_label}
                  />
                  <ActionButton
                    icon={Edit3}
                    intent="edit"
                    onClick={() => abrirModalEditarCanal(lancamento)}
                    size="xs"
                    tone="soft"
                  >
                    Editar canal
                  </ActionButton>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Processado em {formatarDataHora(lancamento.processado_em)}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                <div className="rounded-lg bg-emerald-50 px-3 py-2">
                  <p className="text-xs text-emerald-700">Baixas</p>
                  <p className="font-semibold text-emerald-900">{contarBaixas(lancamento)}</p>
                </div>
                <div className="rounded-lg bg-blue-50 px-3 py-2">
                  <p className="text-xs text-blue-700">Financeiro</p>
                  <p className="font-semibold text-blue-900">
                    {contarLancamentosFinanceiros(lancamento)}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-600">Itens</p>
                  <p className="font-semibold text-slate-900">{lancamento.total_itens || 0}</p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-600">Tarifa</p>
                  <p className="font-semibold text-slate-900">
                    {lancamento.tarifa_envio ? formatMoneyBRL(lancamento.tarifa_envio.valor) : "-"}
                  </p>
                </div>
              </div>
            </div>

            <details className="mt-3">
              <summary className="cursor-pointer text-sm font-medium text-blue-700">
                Ver itens da baixa
              </summary>
              <div className="mt-3">
                <DataTable
                  columns={[
                    { key: "sku", header: "SKU", render: (item) => item.sku || "-" },
                    { key: "produto", header: "Produto", render: (item) => item.nome || "-" },
                    {
                      key: "quantidade",
                      header: "Qtd",
                      align: "right",
                      render: (item) => item.quantidade,
                    },
                    {
                      key: "antes",
                      header: "Antes",
                      align: "right",
                      render: (item) => item.estoque_anterior,
                    },
                    {
                      key: "depois",
                      header: "Depois",
                      align: "right",
                      render: (item) => item.estoque_novo,
                    },
                  ]}
                  data={lancamento.itens || []}
                  emptyMessage="Nenhum item registrado nesta baixa."
                  getRowKey={(item) =>
                    `${lancamento.numero_nf}-${item.movimentacao_id || item.produto_id || item.sku}`
                  }
                  theadClassName="bg-slate-50"
                />
              </div>
            </details>
          </div>
        ))}
      </div>
    </Panel>
  );
}
