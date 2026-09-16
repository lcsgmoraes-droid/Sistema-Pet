import { useCallback, useEffect, useRef, useState } from "react";

import {
  extrairMensagemNFe,
  prevalidarNotaFiscal,
  resolverPendenciasNotaFiscal,
  temPendenciasFiscais,
} from "../utils/nfeFiscalAssistida";

const DOCUMENT_TYPES = ["nfce", "nfe"];

function initialState(loading = false) {
  return {
    nfce: { loading, validation: null, error: "" },
    nfe: { loading, validation: null, error: "" },
  };
}

export function useFiscalDocumentAvailability(saleId) {
  const [statuses, setStatuses] = useState(() => initialState(Boolean(saleId)));
  const requestId = useRef(0);

  const reload = useCallback(async () => {
    if (!saleId) {
      setStatuses(initialState(false));
      return;
    }

    const currentRequest = requestId.current + 1;
    requestId.current = currentRequest;
    setStatuses((current) => ({
      nfce: { ...current.nfce, loading: true, error: "" },
      nfe: { ...current.nfe, loading: true, error: "" },
    }));

    const results = await Promise.allSettled(
      DOCUMENT_TYPES.map((documentType) =>
        prevalidarNotaFiscal({ vendaId: saleId, tipoNota: documentType }),
      ),
    );

    if (requestId.current !== currentRequest) return;

    setStatuses(
      Object.fromEntries(
        DOCUMENT_TYPES.map((documentType, index) => {
          const result = results[index];
          return [
            documentType,
            result.status === "fulfilled"
              ? { loading: false, validation: result.value, error: "" }
              : {
                  loading: false,
                  validation: null,
                  error: extrairMensagemNFe(result.reason),
                },
          ];
        }),
      ),
    );
  }, [saleId]);

  useEffect(() => {
    reload();
    return () => {
      requestId.current += 1;
    };
  }, [reload]);

  const resolvePending = useCallback(
    async (documentType) => {
      const validation = statuses[documentType]?.validation;
      if (!saleId || !temPendenciasFiscais(validation)) return false;

      const corrected = await resolverPendenciasNotaFiscal({
        validacao: validation,
        vendaId: saleId,
        tipoNota: documentType,
      });
      if (corrected) await reload();
      return corrected;
    },
    [reload, saleId, statuses],
  );

  return { reload, resolvePending, statuses };
}
