import { useState } from "react";
import { Download, Printer, RefreshCw, Send } from "lucide-react";
import BotaoCancelar from "../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../../components/v2/BotaoInteracao/BotaoInteracao";
import InputCheck from "../../../components/v2/InputCheck/InputCheck";
import ModalPadrao from "../../../components/v2/ModalPadrao/ModalPadrao";
import { formatMoneyBRL } from "../../../utils/formatters";
import { canIssueOrder, STATUS_FISCAIS } from "./amazonFiscalUtils";

export default function AmazonFiscalOrderDialog({ fiscal }) {
  const [historicalConsent, setHistoricalConsent] = useState(false);
  const order = fiscal.detail;
  const source = order?.source || {};
  const address = source.recipient?.address || {};
  const historical = order?.blockers?.some(
    (item) => item.code === "historical_order_requires_review",
  );
  return (
    <ModalPadrao
      titulo={order ? `Pedido Amazon ${order.external_order_id}` : "Revisar pedido fiscal"}
      tamanho="ampla"
      onFechar={fiscal.closeOrder}
      rodape={
        <BotaoCancelar disabled={fiscal.busy} onClick={fiscal.closeOrder}>
          Voltar
        </BotaoCancelar>
      }
    >
      {fiscal.error && (
        <p role="alert" className="mb-4 text-sm text-red-700 dark:text-red-300">
          {fiscal.error}
        </p>
      )}
      {fiscal.detailLoading ? (
        <p role="status">Carregando dados fiscais do pedido...</p>
      ) : order ? (
        <div className="space-y-5 text-sm text-slate-800 dark:text-slate-100">
          <div className="grid gap-3 sm:grid-cols-3">
            <p>
              Situação SEFAZ:{" "}
              <strong>{STATUS_FISCAIS[order.status] || "Situação desconhecida"}</strong>
            </p>
            <p>
              Conta Amazon: <strong>{order.seller_id}</strong>
            </p>
            <p>
              NF-e: <strong>{order.numero || "Numeração automática na emissão"}</strong>
            </p>
          </div>
          <p className="rounded-lg bg-blue-50 p-3 text-blue-900 dark:bg-blue-950/30 dark:text-blue-200">
            A autorização da SEFAZ confirma a emissão fiscal. O EcommerceAI acompanha o envio do XML
            e o aceite pela Amazon separadamente.
          </p>
          {order.motivo && <p role="status">Retorno do emissor: {order.motivo}</p>}
          {(order.blockers || []).length > 0 && (
            <div
              role="status"
              className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-800 dark:bg-amber-950/20 dark:text-amber-200"
            >
              <p className="font-semibold">Pendências para emissão</p>
              <ul className="mt-2 list-inside list-disc space-y-1">
                {order.blockers.map((blocker, index) => (
                  <li key={`${blocker.code}-${index}`}>{blocker.message}</li>
                ))}
              </ul>
            </div>
          )}
          <section className="space-y-2">
            <h4 className="font-semibold">Destinatário</h4>
            <p>{source.recipient?.name || order.recipient_name || "Nome ainda não recebido"}</p>
            <p>CPF/CNPJ: {source.recipient?.document || "Documento ainda não recebido"}</p>
            <p>
              {[
                address.street,
                address.number,
                address.complement,
                address.district,
                address.city,
                address.state,
                address.postal_code,
              ]
                .filter(Boolean)
                .join(", ") || "Endereço ainda não recebido"}
            </p>
          </section>
          <section className="space-y-2">
            <h4 className="font-semibold">Itens do pedido</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr>
                    <th className="p-2">SKU Amazon</th>
                    <th className="p-2">Quantidade</th>
                    <th className="p-2">Preço unitário</th>
                    <th className="p-2">Desconto informado</th>
                  </tr>
                </thead>
                <tbody>
                  {(source.items || []).map((item) => (
                    <tr
                      key={item.external_item_id}
                      className="border-t border-slate-200 dark:border-slate-700"
                    >
                      <td className="p-2">{item.seller_sku}</td>
                      <td className="p-2">{item.quantity}</td>
                      <td className="p-2">{formatMoneyBRL(Number(item.unit_price))}</td>
                      <td className="p-2">{formatMoneyBRL(Number(item.discount_amount || 0))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="space-y-2">
            <h4 className="font-semibold">Totais e pagamentos documentados</h4>
            <p>
              Produtos: {formatMoneyBRL(Number(source.totals?.products || 0))} · Desconto de origem:{" "}
              {formatMoneyBRL(Number(source.totals?.discount || 0))} · Frete:{" "}
              {formatMoneyBRL(Number(source.totals?.freight || 0))}
            </p>
            <p>
              Total fiscal preparado:{" "}
              <strong>
                {formatMoneyBRL(Number(order.total ?? source.totals?.invoice_total ?? 0))}
              </strong>
            </p>
            <p>
              Pagamento documentado pelo comprador:{" "}
              {source.buyer_paid_total == null
                ? "Ainda não recebido"
                : formatMoneyBRL(Number(source.buyer_paid_total))}
            </p>
            <ul className="list-inside list-disc">
              {(source.payments || []).map((payment, index) => (
                <li key={index}>
                  Meio fiscal {payment.fiscal_method}: {formatMoneyBRL(Number(payment.amount))}
                </li>
              ))}
            </ul>
            {order.discount_audit && (
              <div className="space-y-1 rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                <p>
                  Política aplicada:{" "}
                  {order.discount_audit.policy === "buyer_payment_total"
                    ? "Ajustar ao pagamento documentado"
                    : "Somente descontos explícitos do pedido"}
                </p>
                <p>
                  Desconto adicional rateado:{" "}
                  {formatMoneyBRL(Number(order.discount_audit.extra_discount || 0))}
                  {" · "}Desconto fiscal total:{" "}
                  {formatMoneyBRL(Number(order.discount_audit.effective_discount || 0))}
                </p>
                <p className="text-slate-600 dark:text-slate-300">
                  Valores e política preservados no histórico de revisão fiscal deste pedido.
                </p>
              </div>
            )}
          </section>
          {order.chave && <p className="break-all">Chave da nota: {order.chave}</p>}
          {historical && (
            <div className="space-y-2 rounded-lg border border-amber-200 p-3 dark:border-amber-800">
              <p>
                Este pedido é anterior à ativação. Confira se já existe uma nota emitida antes de
                liberar uma nova emissão.
              </p>
              <InputCheck
                id="amazon-historical-review"
                label="Revisei o histórico e confirmo que este pedido pode seguir para emissão"
                checked={historicalConsent}
                onChange={setHistoricalConsent}
                disabled={fiscal.busy}
              />
              <BotaoInteracao
                disabled={!historicalConsent || fiscal.busy}
                onClick={() => fiscal.reviewHistorical(order)}
              >
                Registrar revisão do pedido anterior
              </BotaoInteracao>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <BotaoInteracao
              icon={Send}
              disabled={!canIssueOrder(order) || fiscal.busy}
              loading={fiscal.busy}
              onClick={() => fiscal.issue(order)}
            >
              Confirmar emissão da NF-e
            </BotaoInteracao>
            <BotaoInteracao
              icon={RefreshCw}
              disabled={fiscal.busy}
              onClick={() => fiscal.consult(order)}
            >
              Consultar situação fiscal
            </BotaoInteracao>
            <BotaoInteracao
              icon={Download}
              disabled={!order.xml_available || fiscal.busy}
              onClick={() => fiscal.download(order, "xml")}
            >
              Baixar XML autorizado
            </BotaoInteracao>
            <BotaoInteracao
              icon={Printer}
              disabled={!order.danfe_available || fiscal.busy}
              onClick={() => fiscal.download(order, "danfe")}
            >
              Baixar DANFE
            </BotaoInteracao>
          </div>
        </div>
      ) : (
        <p>Não foi possível abrir os dados. Volte à caixa de pedidos e tente novamente.</p>
      )}
    </ModalPadrao>
  );
}
