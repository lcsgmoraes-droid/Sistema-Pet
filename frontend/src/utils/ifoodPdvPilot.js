import { CANAL_IFOOD, normalizeSalesChannel } from "./salesChannel.js";

export function isIfoodManualPaymentBlocked(sale) {
  return (
    normalizeSalesChannel(sale?.canal) === CANAL_IFOOD &&
    !(sale?.ifood_pdv_pilot?.enabled === true && sale.ifood_pdv_pilot.payment_mode === "offline")
  );
}

export function canFinalizeIfoodOnlinePdvPilot(bridge) {
  const saleId = Number(bridge?.sale_id);
  return Boolean(
    bridge?.enabled &&
    bridge?.payment_mode === "online" &&
    bridge?.can_finalize_online === true &&
    bridge?.status === "reserved" &&
    Number.isSafeInteger(saleId) &&
    saleId > 0 &&
    bridge?.ifood_order_id,
  );
}
