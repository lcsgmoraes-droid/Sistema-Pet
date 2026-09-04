import { api } from "./api";

const BASE = "/nfse-manual";

export const nfseManualApi = {
  obterPorConsulta: (consultaId) => api.get(`${BASE}/consultas/${consultaId}`),
  prepararConsulta: (consultaId, payload = {}) =>
    api.post(`${BASE}/consultas/${consultaId}/preparar`, payload),
  listar: (status) => api.get(`${BASE}/documentos`, { params: status ? { status } : undefined }),
  atualizarRascunho: (documentoId, payload) =>
    api.put(`${BASE}/documentos/${documentoId}/rascunho`, payload),
  registrarEmitida: (documentoId, payload) =>
    api.post(`${BASE}/documentos/${documentoId}/registrar`, payload),
  marcarCancelada: (documentoId, payload) =>
    api.post(`${BASE}/documentos/${documentoId}/marcar-cancelada`, payload),
  enviarAnexo: (documentoId, tipo, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post(`${BASE}/documentos/${documentoId}/anexos/${tipo}`, formData);
  },
  baixarAnexo: (documentoId, tipo) =>
    api.get(`${BASE}/documentos/${documentoId}/anexos/${tipo}`, {
      responseType: "blob",
    }),
};

export function baixarBlob(response, nomeArquivo) {
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
