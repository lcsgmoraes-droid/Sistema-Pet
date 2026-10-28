import { ArrowRight, CheckCircle } from "lucide-react";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import LinkPadrao from "../v2/LinkPadrao/LinkPadrao";
import IfoodPdvOnlineResumo from "./IfoodPdvOnlineResumo";
import { canFinalizeIfoodOnlinePdvPilot } from "../../utils/ifoodPdvPilot";

const STATUS_LABELS = {
  not_imported: "Ainda não enviado ao PDV",
  reserved: "Estoque reservado no CorePet",
  sold: "Venda finalizada no CorePet",
  cancelled: "Cancelado no CorePet",
  blocked: "Pedido fora do piloto",
};

export function canImportIfoodPdvPilot(bridge) {
  return Boolean(
    bridge?.enabled && bridge?.eligible && bridge?.status === "not_imported" && !bridge?.sale_id,
  );
}

export default function IfoodPedidoPdvPilot({
  bridge,
  busy = false,
  onImport,
  onFinalizeOnline,
  showSaleLink = true,
}) {
  if (!bridge?.enabled) return null;

  const saleId = Number(bridge.sale_id);
  const hasSale = Number.isSafeInteger(saleId) && saleId > 0;
  const reservedQuantity =
    bridge.reserved_quantity === null || bridge.reserved_quantity === undefined
      ? Number.NaN
      : Number(bridge.reserved_quantity);

  return (
    <section
      aria-label="Piloto do PDV em DEV"
      className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm dark:border-blue-900 dark:bg-blue-950/30"
    >
      <h4 className="font-semibold text-slate-900 dark:text-slate-100">Piloto do PDV em DEV</h4>
      <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
        Somente o pedido de teste autorizado e o SKU 018631.1 podem reservar estoque neste piloto.{" "}
        {bridge.payment_mode === "online"
          ? "A baixa acontece somente ao usar Concluir venda e baixar estoque."
          : "A baixa acontece ao finalizar a venda no PDV."}
      </p>
      <p role="status" className="mt-3 font-medium text-slate-900 dark:text-slate-100">
        {STATUS_LABELS[bridge.status] || "Conferência pendente"}
      </p>
      {bridge.status === "cancelled" ? (
        <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
          Cancelamento registrado somente no CorePet. Confira a situação do pedido no iFood.
        </p>
      ) : bridge.reason ? (
        <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">{bridge.reason}</p>
      ) : null}
      <IfoodPdvOnlineResumo bridge={bridge} />
      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
        <div>
          <dt className="text-xs text-slate-500 dark:text-slate-400">Reserva ativa deste pedido</dt>
          <dd className="font-medium text-slate-900 dark:text-slate-100">
            {Number.isFinite(reservedQuantity)
              ? reservedQuantity.toLocaleString("pt-BR", { maximumFractionDigits: 3 })
              : "Não informada"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500 dark:text-slate-400">Baixa de estoque</dt>
          <dd className="font-medium text-slate-900 dark:text-slate-100">
            {bridge.stock_decreased === true
              ? "Registrada"
              : bridge.stock_decreased === false
                ? "Não realizada"
                : "Não informada"}
          </dd>
        </div>
        {bridge.status === "cancelled" && (
          <div>
            <dt className="text-xs text-slate-500 dark:text-slate-400">Recomposição do estoque</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {bridge.stock_restored === true
                ? "Lotes originais recompostos"
                : bridge.stock_decreased === false
                  ? "Reserva liberada, sem entrada física"
                  : "Conferência pendente"}
            </dd>
          </div>
        )}
      </dl>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        {canImportIfoodPdvPilot(bridge) ? (
          <BotaoInteracao
            disabled={busy}
            icon={ArrowRight}
            loading={busy}
            onClick={onImport}
            tamanho="pequeno"
          >
            Enviar ao PDV de teste
          </BotaoInteracao>
        ) : null}
        {canFinalizeIfoodOnlinePdvPilot(bridge) && onFinalizeOnline ? (
          <BotaoInteracao
            disabled={busy}
            icon={CheckCircle}
            loading={busy}
            onClick={onFinalizeOnline}
            tamanho="pequeno"
          >
            Concluir venda e baixar estoque
          </BotaoInteracao>
        ) : null}
        {hasSale && showSaleLink ? (
          <LinkPadrao to={`/pdv?venda=${saleId}`}>Abrir venda #{saleId} no PDV</LinkPadrao>
        ) : null}
      </div>
    </section>
  );
}
