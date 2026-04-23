import api from "../api";

export const getCampanhaValidadeConfig = () =>
  api.get("/campanhas/validade/config");

export const salvarCampanhaValidadeConfig = (payload) =>
  api.put("/campanhas/validade/config", payload);

export const criarExclusaoCampanhaValidade = (payload) =>
  api.post("/campanhas/validade/exclusoes", payload);

export const removerExclusaoCampanhaValidade = (exclusaoId) =>
  api.delete(`/campanhas/validade/exclusoes/${exclusaoId}`);

export default {
  getCampanhaValidadeConfig,
  salvarCampanhaValidadeConfig,
  criarExclusaoCampanhaValidade,
  removerExclusaoCampanhaValidade,
};
