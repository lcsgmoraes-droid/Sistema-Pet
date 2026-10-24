import api from "../api";

// Preparação local do catálogo. Estes endpoints não publicam no iFood.
export const getIfoodCatalogo = (params = {}, config = {}) =>
  api.get("/integracoes/ifood/catalogo/gestao", { ...config, params });

export const previewIfoodProduto = (payload, config = {}) =>
  api.post("/integracoes/ifood/catalogo/produto/preview", payload, config);

export const simularPrecoIfoodProduto = (payload, config = {}) =>
  api.post("/integracoes/ifood/catalogo/produto/simular-preco", payload, config);

export const getIfoodConfiguracao = (config = {}) => api.get("/integracoes/ifood/status", config);

export const salvarIfoodConfiguracao = (payload) =>
  api.put("/integracoes/ifood/catalogo/configuracao", payload);

// Consulta financeira independente do catalogo. Nao publica nem opera pedidos.
export const getIfoodFinanceiroStatus = (config = {}) =>
  api.get("/integracoes/ifood/financeiro/status", config);

export const getIfoodFinanceiroRelatorio = (params, config = {}) =>
  api.get("/integracoes/ifood/financeiro/relatorio", { ...config, params });

export const sincronizarIfoodFinanceiro = (payload, config = {}) =>
  api.post("/integracoes/ifood/financeiro/sincronizar", payload, config);

export const salvarIfoodCustosPedido = (orderId, payload, config = {}) =>
  api.put(
    `/integracoes/ifood/financeiro/pedidos/${encodeURIComponent(orderId)}/custos`,
    payload,
    config,
  );
