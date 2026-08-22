import { api } from "./api";

export async function obterResumoGruposEmpresas() {
  const { data } = await api.get("/grupos-empresas/resumo");
  return data;
}

export async function criarGrupoEmpresa(nome) {
  const { data } = await api.post("/grupos-empresas", { nome });
  return data;
}

export async function convidarEmpresa(grupoId, codigoEmpresa) {
  const { data } = await api.post(`/grupos-empresas/${grupoId}/convites`, {
    codigo_empresa: codigoEmpresa,
  });
  return data;
}

export async function responderConviteGrupo(conviteId, aceitar) {
  const acao = aceitar ? "aceitar" : "recusar";
  const { data } = await api.post(`/grupos-empresas/convites/${conviteId}/${acao}`);
  return data;
}

export async function removerEmpresaGrupo(grupoId, empresaId) {
  const { data } = await api.delete(
    `/grupos-empresas/${grupoId}/membros/${encodeURIComponent(empresaId)}`,
  );
  return data;
}
