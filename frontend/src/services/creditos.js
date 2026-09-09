import api from "../api";

export const obterCatalogoCreditos = () => api.get("/creditos/catalogo");
export const obterCarteiraCreditos = () => api.get("/creditos/carteira");
export const obterExtratoCreditos = () => api.get("/creditos/extrato");
export const orcarCreditos = (serviceCode, requestPayload) =>
  api.post("/creditos/orcamento", {
    service_code: serviceCode,
    request_payload: requestPayload,
  });
export const consultarOperacaoCredito = (operationId) =>
  api.get(`/creditos/operacoes/${encodeURIComponent(operationId)}`);
