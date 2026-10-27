import { Download, Eye, Printer, RefreshCw, Send } from "lucide-react";
import BotaoInteracao from "../../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoMenuAcoes from "../../../components/v2/BotaoMenuAcoes/BotaoMenuAcoes";
import InputCombobox from "../../../components/v2/InputCombobox/InputCombobox";
import { formatMoneyBRL } from "../../../utils/formatters";
import { canIssueOrder, STATUS_FISCAIS } from "./amazonFiscalUtils";

export default function AmazonFiscalOrders({ fiscal }) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="font-semibold">Caixa de pedidos fiscais Amazon</h3>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Pedidos recebidos do EcommerceAI. Revise as pendências e acompanhe a emissão na SEFAZ.
          </p>
        </div>
        <div className="w-full sm:w-64">
          <InputCombobox
            id="amazon-fiscal-status"
            label="Situação fiscal"
            value={fiscal.status}
            opcoes={[
              { value: "", label: "Todas" },
              ...Object.entries(STATUS_FISCAIS).map(([value, label]) => ({ value, label })),
            ]}
            onChange={fiscal.filter}
            permitirLimpar={false}
          />
        </div>
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="w-full text-left text-sm">
          <thead>
            <tr>
              <th className="p-3">Ações</th>
              <th className="p-3">Pedido / conta</th>
              <th className="p-3">Destinatário</th>
              <th className="p-3">Total fiscal</th>
              <th className="p-3">Situação SEFAZ</th>
              <th className="p-3">Pendências</th>
            </tr>
          </thead>
          <tbody>
            {fiscal.orders.map((order) => (
              <tr
                key={order.id}
                className="border-t border-slate-200 align-top dark:border-slate-700"
              >
                <td className="p-3">
                  <BotaoMenuAcoes
                    rotulo={`Ações do pedido ${order.external_order_id}`}
                    acoes={[
                      {
                        icon: Eye,
                        label: "Revisar pedido",
                        onClick: () => fiscal.openOrder(order),
                        disabled: fiscal.busy,
                      },
                      {
                        icon: Send,
                        label: "Emitir NF-e",
                        onClick: () => fiscal.openOrder(order),
                        disabled: fiscal.busy || !canIssueOrder(order),
                      },
                      {
                        icon: RefreshCw,
                        label: "Consultar situação fiscal",
                        onClick: () => fiscal.consult(order),
                        disabled: fiscal.busy,
                      },
                      {
                        icon: Download,
                        label: "Baixar XML autorizado",
                        onClick: () => fiscal.download(order, "xml"),
                        disabled: fiscal.busy || !order.xml_available,
                      },
                      {
                        icon: Printer,
                        label: "Baixar DANFE",
                        onClick: () => fiscal.download(order, "danfe"),
                        disabled: fiscal.busy || !order.danfe_available,
                      },
                    ]}
                  />
                </td>
                <td className="p-3">
                  <p className="font-medium">{order.external_order_id}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {order.seller_id}
                  </p>
                </td>
                <td className="p-3">{order.recipient_name || "Ainda não recebido"}</td>
                <td className="p-3">
                  {order.total == null ? "Aguardando revisão" : formatMoneyBRL(Number(order.total))}
                </td>
                <td className="p-3">
                  <p>{STATUS_FISCAIS[order.status] || "Situação desconhecida"}</p>
                  {order.numero && <p className="mt-1 text-xs">NF-e {order.numero}</p>}
                </td>
                <td className="max-w-sm p-3">
                  {(order.blockers || []).length ? (
                    <ul className="space-y-1 text-amber-800 dark:text-amber-300">
                      {order.blockers.map((item, index) => (
                        <li key={`${item.code}-${index}`}>{item.message}</li>
                      ))}
                    </ul>
                  ) : (
                    "Sem pendências informadas"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!fiscal.orders.length && (
          <p className="p-4 text-sm text-slate-500 dark:text-slate-400">
            Nenhum pedido encontrado. Ative a fila fiscal da conta no EcommerceAI para receber os
            pedidos.
          </p>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <p>
          {fiscal.total} pedido(s) · página {fiscal.page}
        </p>
        <div className="flex gap-2">
          <BotaoInteracao
            tamanho="pequeno"
            disabled={fiscal.page === 1 || fiscal.refreshing}
            onClick={() => fiscal.setPage(fiscal.page - 1)}
          >
            Página anterior
          </BotaoInteracao>
          <BotaoInteracao
            tamanho="pequeno"
            disabled={fiscal.page * 25 >= fiscal.total || fiscal.refreshing}
            onClick={() => fiscal.setPage(fiscal.page + 1)}
          >
            Próxima página
          </BotaoInteracao>
        </div>
      </div>
    </section>
  );
}
