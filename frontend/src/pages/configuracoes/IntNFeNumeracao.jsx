import { useCallback, useEffect, useRef, useState } from "react";
import IntNFeNumeracaoView from "./IntNFeNumeracaoView";
import { numberingRows, prepareNumbering } from "./intnfeNumeracao.mjs";

export default function IntNFeNumeracao({ apiClient, disabled = false, onBusy, onData }) {
  const [rows, setRows] = useState(null);
  const [form, setForm] = useState({
    modelo: "55",
    serie: "1",
    ambiente_codigo: "2",
    proximo_numero: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [review, setReview] = useState(null);
  const mounted = useRef(false);
  const inFlight = useRef(false);
  const requestController = useRef(null);

  const execute = useCallback(
    async (payload = null) => {
      if (inFlight.current) return;
      inFlight.current = true;
      const controller = new AbortController();
      requestController.current = controller;
      const isCurrent = () => mounted.current && requestController.current === controller;
      setBusy(true);
      onBusy?.(true);
      setError("");
      setMessage("");
      setReview(null);
      try {
        const response = payload
          ? await apiClient.put("/intnfe/numeracao", payload, { signal: controller.signal })
          : await apiClient.get("/intnfe/numeracao", { signal: controller.signal });
        const updated = numberingRows(response.data);
        if (isCurrent()) {
          setRows(updated);
          onData?.(response.data);
          if (payload) {
            setMessage(
              response.data.mensagem || "Ajuste confirmado. Confira a sequência atual abaixo.",
            );
            setForm((previous) => ({ ...previous, proximo_numero: "" }));
          }
        }
      } catch (failure) {
        if (isCurrent()) {
          // Falha de escrita pode ocorrer depois da aplicacao. Exigir nova consulta, sem repetir PUT.
          setRows(null);
          onData?.(null);
          const detail = failure?.response?.data?.detail;
          const text = typeof detail === "string" ? detail : detail?.mensagem;
          setError(
            text ||
              (payload
                ? "Não foi possível confirmar o ajuste. Ele pode ter sido aplicado. Consulte a numeração antes de tentar novamente."
                : "Não foi possível consultar a numeração. Tente consultar novamente."),
          );
        }
      } finally {
        if (isCurrent()) {
          requestController.current = null;
          inFlight.current = false;
          setBusy(false);
          onBusy?.(false);
        }
      }
    },
    [apiClient, onBusy, onData],
  );

  useEffect(() => {
    mounted.current = true;
    execute();
    return () => {
      mounted.current = false;
      // Descarta a requisicao anterior, inclusive eventual renovacao de sessao.
      requestController.current?.abort();
      requestController.current = null;
      inFlight.current = false;
      onBusy?.(false);
    };
  }, [execute, onBusy]);

  const change = (values) => {
    if (inFlight.current || disabled) return;
    setForm((previous) => ({ ...previous, ...values }));
    setReview(null);
    setMessage("");
  };

  return (
    <IntNFeNumeracaoView
      rows={rows}
      form={form}
      busy={busy || disabled}
      error={error}
      message={message}
      review={review}
      onChange={change}
      onReload={() => execute()}
      onReview={(event) => {
        event.preventDefault();
        if (inFlight.current || disabled) return;
        const prepared = prepareNumbering(rows, form);
        if (!prepared.error) setReview(prepared);
      }}
      onCancel={() => setReview(null)}
      onSave={() => {
        if (review && !disabled) execute(review.payload);
      }}
    />
  );
}
