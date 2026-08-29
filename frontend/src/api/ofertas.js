import api from "../api";

export const getContextoOfertas = () => api.get("/ofertas/contexto");

export const getProdutosOfertas = (params = {}) => api.get("/ofertas/produtos", { params });

export const getSugestoesOfertas = (params = {}) => api.get("/ofertas/sugestoes", { params });

export const gerarImagemOferta = (formData) =>
  api.post("/ofertas/imagens/gerar", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 180000,
  });

export const publicarOferta = (formData) =>
  api.post("/ofertas/publicacoes", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 180000,
  });

export const getPublicacoesOfertas = () => api.get("/ofertas/publicacoes");

export const desativarPublicacaoOferta = (id) => api.post(`/ofertas/publicacoes/${id}/desativar`);
