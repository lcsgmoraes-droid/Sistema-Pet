import { useCallback, useEffect, useRef, useState } from "react";
import IntNFeNumeracaoView from "./IntNFeNumeracaoView";
import { currentSequence, numberingRows, prepareNumbering } from "./intnfeNumeracao.mjs";

const emptyForms = () => ({
  1: {
    55: { serie: "1", proximo_numero: "", usar_no_corepet: false },
    65: { serie: "1", proximo_numero: "", usar_no_corepet: false },
  },
  2: {
    55: { serie: "1", proximo_numero: "", usar_no_corepet: false },
    65: { serie: "1", proximo_numero: "", usar_no_corepet: false },
  },
});

export default function IntNFeNumeracao({
  apiClient,
  disabled = false,
  environment = 2,
  onBusy,
  onData,
  onUseSequence,
  onClearSequence,
}) {
  const [rows, setRows] = useState(null);
  const [forms, setForms] = useState(emptyForms);
  const [models, setModels] = useState({ 1: [55], 2: [55] });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [review, setReview] = useState(null);
  const mounted = useRef(false);
  const inFlight = useRef(false);
  const requestController = useRef(null);

  const execute = useCallback(
    async (payload = null, useForCorePet = false) => {
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
            setMessage(response.data.mensagem || "Sequência fiscal salva.");
            const confirmed = updated.find(
              (row) =>
                row.modelo === payload.modelo &&
                row.ambienteCodigo === payload.ambiente_codigo &&
                Number(row.serie) === Number(payload.serie),
            );
            if (useForCorePet && confirmed) {
              onUseSequence?.({
                modelo: payload.modelo,
                serie: String(Number(payload.serie)),
                proximoNumero: confirmed.proximoNumero,
                pendente: false,
              });
            }
            setForms((previous) => ({
              ...previous,
              [payload.ambiente_codigo]: {
                ...previous[payload.ambiente_codigo],
                [payload.modelo]: {
                  ...previous[payload.ambiente_codigo][payload.modelo],
                  proximo_numero: "",
                },
              },
            }));
          }
        }
      } catch (failure) {
        if (isCurrent()) {
          setRows(null);
          onData?.(null);
          const detail = failure?.response?.data?.detail;
          const text = typeof detail === "string" ? detail : detail?.mensagem;
          setError(
            text ||
              (payload
                ? "Não foi possível confirmar o ajuste. Ele pode ter sido aplicado. Consulte as sequências antes de tentar novamente."
                : "Não foi possível consultar as sequências. Tente novamente."),
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
    [apiClient, onBusy, onData, onUseSequence],
  );

  useEffect(() => {
    mounted.current = true;
    execute();
    return () => {
      mounted.current = false;
      requestController.current?.abort();
      requestController.current = null;
      inFlight.current = false;
      onBusy?.(false);
    };
  }, [execute, onBusy]);

  useEffect(() => {
    setReview(null);
    setError("");
    setMessage("");
  }, [environment]);

  const change = (model, values) => {
    if (inFlight.current || disabled) return;
    const nextForm = { ...forms[environment][model], ...values };
    setForms((previous) => ({
      ...previous,
      [environment]: { ...previous[environment], [model]: nextForm },
    }));
    if (nextForm.usar_no_corepet && /^[0-9]{1,3}$/.test(nextForm.serie)) {
      const current = currentSequence(rows || [], nextForm.serie, environment, model);
      const hasNumber = nextForm.proximo_numero !== "";
      const validNumber =
        /^\d{1,9}$/.test(nextForm.proximo_numero) && Number(nextForm.proximo_numero) > 0;
      onUseSequence?.({
        modelo: model,
        serie: String(Number(nextForm.serie)),
        proximoNumero: validNumber
          ? Number(nextForm.proximo_numero)
          : (current?.proximoNumero ?? 1),
        pendente: Boolean(
          hasNumber &&
          (!validNumber || !current || Number(nextForm.proximo_numero) !== current.proximoNumero),
        ),
      });
    }
    setReview(null);
    setMessage("");
  };

  const toggleUse = (model, checked) => {
    change(model, { usar_no_corepet: checked });
    if (!checked) {
      onClearSequence?.({ modelo: model });
    }
  };

  return (
    <IntNFeNumeracaoView
      rows={rows}
      forms={forms[environment]}
      models={models[environment]}
      environment={environment}
      busy={busy || disabled}
      error={error}
      message={message}
      review={review}
      onChange={change}
      onToggleUse={toggleUse}
      onReload={() => execute()}
      onAddNfce={() => setModels((current) => ({ ...current, [environment]: [55, 65] }))}
      onRemoveNfce={() => {
        setModels((current) => ({ ...current, [environment]: [55] }));
        change(65, { usar_no_corepet: false });
        onClearSequence?.({ modelo: 65 });
      }}
      onReview={(model) => {
        if (inFlight.current || disabled) return;
        const form = {
          ...forms[environment][model],
          modelo: String(model),
          ambiente_codigo: String(environment),
        };
        const prepared = prepareNumbering(rows, form);
        if (!prepared.error) setReview({ model, ...prepared });
      }}
      onCancel={() => setReview(null)}
      onSave={() => {
        if (review && !disabled) {
          execute(review.payload, forms[environment][review.model].usar_no_corepet);
        }
      }}
    />
  );
}
