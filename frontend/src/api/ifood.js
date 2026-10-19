import api from "../api";

// Preparação local do catálogo. Estes endpoints não publicam no iFood.
export const getIfoodCatalogo = (params = {}, config = {}) =>
  api.get("/integracoes/ifood/catalogo/gestao", { ...config, params });

export const previewIfoodProduto = (payload, config = {}) =>
  api.post("/integracoes/ifood/catalogo/produto/preview", payload, config);

export const getIfoodConfiguracao = (config = {}) => api.get("/integracoes/ifood/status", config);

export const salvarIfoodConfiguracao = (payload) =>
  api.put("/integracoes/ifood/catalogo/configuracao", payload);
