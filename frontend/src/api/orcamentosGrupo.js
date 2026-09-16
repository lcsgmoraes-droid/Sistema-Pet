import { api } from "../services/api";

const BASE = "/orcamentos-grupo";

export const orcamentosGrupoApi = {
  status: () => api.get(`${BASE}/status`),
  buscarConfiguracao: () => api.get(`${BASE}/configuracao`),
  salvarConfiguracao: (data) => api.put(`${BASE}/configuracao`, data),
  buscarPessoas: (search) => api.get(`${BASE}/pessoas`, { params: { search } }),
  listarEmpresas: (incluirInativas = false) =>
    api.get(`${BASE}/empresas`, { params: { incluir_inativas: incluirInativas } }),
  adicionarEmpresa: (data) => api.post(`${BASE}/empresas`, data),
  atualizarEmpresa: (id, data) => api.patch(`${BASE}/empresas/${id}`, data),
  removerEmpresa: (id) => api.delete(`${BASE}/empresas/${id}`),
  listarOrcamentos: () => api.get(BASE),
  criarOrcamento: (data) => api.post(BASE, data),
  detalharOrcamento: (id) => api.get(`${BASE}/${id}`),
  baixarPdf: (id, cotacaoId) =>
    api.get(`${BASE}/${id}/pdf`, {
      params: cotacaoId ? { cotacao_id: cotacaoId } : {},
      responseType: "blob",
    }),
};

export function baixarBlob(blob, nome) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
