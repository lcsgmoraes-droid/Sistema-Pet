import { useRef, useState } from "react";
import api from "../../api";
import { canFinalizeIfoodOnlinePdvPilot } from "../../utils/ifoodPdvPilot";
import IfoodPedidoPdvPilot from "./IfoodPedidoPdvPilot";
import IfoodPdvOnlineResumo from "./IfoodPdvOnlineResumo";

export default function IfoodPdvOnlineVendaCard({ venda, onUpdated }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const inFlight = useRef(false);
  const currentSale = useRef(venda.id);
  currentSale.current = venda.id;
  const bridge = venda.ifood_pdv_pilot;

  async function finalizeOnline() {
    if (inFlight.current || !canFinalizeIfoodOnlinePdvPilot(bridge)) return;
    inFlight.current = true;
    setBusy(true);
    setMessage("");
    const saleId = venda.id;
    try {
      await api.post(
        `/integracoes/ifood/pedidos/${bridge.ifood_order_id}/piloto-pdv/finalizar-online`,
      );
      if (currentSale.current === saleId) {
        setMessage("Venda concluída. Estoque baixado e repasse a conciliar.");
        await onUpdated?.();
      }
    } catch (error) {
      if (currentSale.current === saleId) {
        const detail = error.response?.data?.detail;
        setMessage(
          typeof detail === "string" ? detail : "Não foi possível concluir a venda online.",
        );
      }
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  return (
    <section aria-label="Venda iFood com pagamento online">
      {bridge?.enabled ? (
        <IfoodPedidoPdvPilot
          bridge={bridge}
          busy={busy}
          onFinalizeOnline={finalizeOnline}
          showSaleLink={false}
        />
      ) : (
        <>
          <IfoodPdvOnlineResumo bridge={bridge} />
          <p className="mt-2 text-sm text-amber-800 dark:text-amber-300">
            {bridge?.reason || "Piloto indisponível."} A cobrança manual deste pedido continua
            bloqueada.
          </p>
        </>
      )}
      {message ? (
        <p role="status" className="mt-2 text-sm text-slate-700 dark:text-slate-200">
          {message}
        </p>
      ) : null}
    </section>
  );
}
