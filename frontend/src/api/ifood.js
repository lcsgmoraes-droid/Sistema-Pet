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

// Piloto assistido: um produto salvo por ação; sem scheduler ou envio por seleção.
const produtoPublicacao = (id) => `/integracoes/ifood/catalogo/produtos/${encodeURIComponent(id)}`;

export const getIfoodPublicacaoProduto = (id, config = {}) =>
  api.get(`${produtoPublicacao(id)}/publicacao`, config);
export const vincularIfoodProduto = (id, payload) =>
  api.put(`${produtoPublicacao(id)}/vinculo`, payload);
export const prepararIfoodPublicacaoProduto = (id, payload) =>
  api.post(`${produtoPublicacao(id)}/preparar`, payload);
export const enviarIfoodPublicacaoProduto = (id, payload) =>
  api.post(`${produtoPublicacao(id)}/enviar`, payload);
export const confirmarIfoodProdutoPortal = (id, payload) =>
  api.post(`${produtoPublicacao(id)}/confirmar-portal`, payload);

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

export const getIfoodRepasses = (params, config = {}) =>
  api.get("/integracoes/ifood/financeiro/repasses", { ...config, params });

export const sincronizarIfoodRepasses = (payload, config = {}) =>
  api.post("/integracoes/ifood/financeiro/repasses/sincronizar", payload, config);

export const getIfoodConciliacaoStatus = (params, config = {}) =>
  api.get("/integracoes/ifood/financeiro/conciliacao/status", { ...config, params });

export const sincronizarIfoodConciliacao = (payload, config = {}) =>
  api.post("/integracoes/ifood/financeiro/conciliacao/sincronizar", payload, config);

export const getIfoodVendasCandidatas = (orderId, params, config = {}) =>
  api.get(
    `/integracoes/ifood/financeiro/pedidos/${encodeURIComponent(orderId)}/vendas-candidatas`,
    {
      ...config,
      params,
    },
  );

export const vincularIfoodVenda = (orderId, payload, config = {}) =>
  api.put(
    `/integracoes/ifood/financeiro/pedidos/${encodeURIComponent(orderId)}/vinculo-venda`,
    payload,
    config,
  );
