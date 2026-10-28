import { useEffect, useRef, useState } from "react";
import api from "../api";
import useIfoodFinancialReportRefresh from "./useIfoodFinancialReportRefresh.js";

/** Atualiza só a apresentação financeira. Nunca reaplica a venda carregada no PDV. */
export default function useIfoodPdvFinancialPresentation({ venda, autoRefresh = false }) {
  const bridge = venda?.ifood_pdv_pilot;
  const saleId = bridge?.sale_id;
  const saleKey = saleId == null ? "" : String(saleId);
  const enabled = Boolean(autoRefresh && saleKey && saleKey === String(venda?.id));
  const financial = bridge?.ifood_financial;
  const profitability = bridge?.ifood_rentabilidade;
  const [presentation, setPresentation] = useState(null);
  const current = useRef(null);
  const active = useRef(false);
  const requestRevision = useRef(0);
  const pendingRequest = useRef(null);
  current.current = { saleKey, financial, profitability, enabled };

  useEffect(() => {
    active.current = enabled;
    requestRevision.current += 1;
    return () => {
      active.current = false;
      requestRevision.current += 1;
      pendingRequest.current?.abort();
      pendingRequest.current = null;
    };
  }, [enabled, saleKey, financial, profitability]);

  async function refresh() {
    const basis = current.current;
    if (!active.current || !basis.enabled) return;
    const revision = ++requestRevision.current;
    pendingRequest.current?.abort();
    const controller = new AbortController();
    pendingRequest.current = controller;
    try {
      const { data } = await api.get(`/vendas/${encodeURIComponent(basis.saleKey)}`, {
        signal: controller.signal,
      });
      const received = data?.ifood_pdv_pilot;
      if (
        !active.current ||
        controller.signal.aborted ||
        requestRevision.current !== revision ||
        current.current.saleKey !== basis.saleKey ||
        current.current.financial !== basis.financial ||
        current.current.profitability !== basis.profitability ||
        String(data?.id) !== basis.saleKey ||
        String(received?.sale_id) !== basis.saleKey
      )
        return;
      const fields = {};
      for (const field of ["ifood_financial", "ifood_rentabilidade"]) {
        if (Object.hasOwn(received, field)) fields[field] = received[field];
      }
      if (Object.keys(fields).length) setPresentation({ ...basis, fields });
    } catch {
      // Mantém os valores conhecidos; timer/foco permitem recuperar a leitura depois.
    } finally {
      if (pendingRequest.current === controller) pendingRequest.current = null;
    }
  }

  useIfoodFinancialReportRefresh({ enabled, refresh });

  return enabled &&
    presentation?.saleKey === saleKey &&
    presentation.financial === financial &&
    presentation.profitability === profitability
    ? { ...bridge, ...presentation.fields }
    : bridge;
}
