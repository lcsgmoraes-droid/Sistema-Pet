import { formatMoneyBRL } from "../../utils/formatters";
import IfoodVendaTaxasResumo from "./IfoodVendaTaxasResumo.jsx";

function amount(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value))
    ? formatMoneyBRL(Number(value))
    : "Não informado";
}

export default function IfoodPdvOnlineResumo({ bridge }) {
  if (bridge?.payment_mode !== "online") return null;
  const checkout = bridge.checkout || {};
  const receivable = bridge.receivable || {};
  const approved = bridge.payment?.status === "approved";
  const cancelled =
    bridge.status === "cancelled" || receivable.status === "cancelled_pending_provider_review";
  const rentabilidade = bridge.ifood_rentabilidade || {};
  const margemConhecida =
    !cancelled &&
    rentabilidade.lucro !== null &&
    rentabilidade.lucro !== undefined &&
    rentabilidade.rentabilidade_status === "complete";
  const lines = [
    ["Produto", checkout.items_total],
    ["Frete do pedido", checkout.delivery_fee],
    ["Valor operacional do pedido", checkout.operational_total],
    ["Taxa de serviço do iFood", checkout.ifood_service_fee],
    ["Total do consumidor", checkout.customer_total],
  ];

  return (
    <div className="mt-3 rounded-lg border border-emerald-200 bg-white p-3 dark:border-emerald-900 dark:bg-slate-950">
      <p className="font-semibold text-slate-900 dark:text-slate-100">Pagamento online no iFood</p>
      <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
        {cancelled
          ? "Cancelamento registrado no CorePet. O pagamento original do pedido permanece no histórico."
          : approved
            ? "Pagamento externo registrado. Sem cobrança na loja."
            : "Pagamento sob responsabilidade do iFood. Sem cobrança na loja."}
      </p>
      <dl className="mt-3 space-y-2 text-sm">
        {lines.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-3">
            <dt className="text-slate-600 dark:text-slate-300">{label}</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">{amount(value)}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-slate-600 dark:text-slate-300">
        A taxa de serviço pertence ao iFood. O total do consumidor não representa o repasse da loja.
      </p>
      <div className="mt-3">
        <IfoodVendaTaxasResumo financeiro={bridge.ifood_financial} />
      </div>
      {margemConhecida && (
        <p className="mt-2 font-semibold text-slate-900 dark:text-slate-100">
          Contribuição da venda: {amount(rentabilidade.lucro)}
          {rentabilidade.margem_sobre_venda != null &&
            ` (${Number(rentabilidade.margem_sobre_venda).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%)`}
        </p>
      )}
      <p className="mt-2 font-medium text-amber-800 dark:text-amber-300">
        {cancelled ? "Estorno iFood a conferir" : "Repasse a conciliar"}
      </p>
      <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
        {cancelled ? (
          "Cancelar no CorePet não cancela o pedido no iFood nem comprova devolução ao consumidor. Confira o cancelamento e o estorno na plataforma; nenhum reembolso foi lançado em caixa ou banco por esta ação."
        ) : (
          <>
            {receivable.received_amount === 0
              ? "Nenhum recebimento em caixa ou banco registrado. "
              : "Recebimento do repasse ainda não comprovado. "}
            {margemConhecida
              ? "A contribuição conhecida não confirma recebimento no banco."
              : "Líquido, data do repasse e margem aguardam o Financial."}
          </>
        )}
      </p>
    </div>
  );
}
