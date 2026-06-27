import { useEffect, useRef } from "react";

import {
  readMercadoPagoPaymentReturn,
  stripMercadoPagoPaymentReturnParams,
} from "../../utils/mercadoPagoPaymentReturn";

export default function useEcommercePaymentReturn({
  location,
  navigate,
  recordOrderId,
  setError,
  setSuccess,
  setView,
}) {
  const handledPaymentReturnSearchRef = useRef("");

  useEffect(() => {
    const paymentReturn = readMercadoPagoPaymentReturn(location.search);
    if (!paymentReturn) return;
    if (handledPaymentReturnSearchRef.current === location.search) return;
    handledPaymentReturnSearchRef.current = location.search;

    setView("pedidos");
    if (paymentReturn.level === "error") {
      setError(`${paymentReturn.title}: ${paymentReturn.message}`);
      setSuccess("");
    } else {
      setError("");
      setSuccess(`${paymentReturn.title}: ${paymentReturn.message}`);
    }

    if (paymentReturn.pedidoId) {
      void recordOrderId(paymentReturn.pedidoId);
    }

    const cleanedSearch = stripMercadoPagoPaymentReturnParams(location.search);
    navigate(`${location.pathname}${cleanedSearch ? `?${cleanedSearch}` : ""}`, { replace: true });
  }, [location.pathname, location.search, navigate, recordOrderId, setError, setSuccess, setView]);
}
