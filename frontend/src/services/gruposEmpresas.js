import { api } from "./api";

export async function obterResumoGruposEmpresas() {
  const { data } = await api.get("/grupos-empresas/resumo");
  return data;
}

export async function obterVisaoConsolidadaGrupo(grupoId, periodoDias = 30) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/visao-consolidada`, {
    params: { periodo_dias: periodoDias },
  });
  return data;
}

export async function obterPedidosGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/pedidos`, { params });
  return data;
}

export async function obterProdutosVendidosGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/produtos-vendidos`, {
    params,
  });
  return data;
}

export async function obterPedidosCompraGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/pedidos-compra`, { params });
  return data;
}

export async function obterContasPagarGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/contas-pagar`, { params });
  return data;
}

export async function obterReposicaoInteligenteGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/reposicao-inteligente`, {
    params,
  });
  return data;
}

export async function obterAnaliseFinanceiraGrupo(grupoId) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/analise-financeira`);
  return data;
}

export async function buscarProdutosGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/produtos`, { params });
  return data;
}

export async function obterVinculosProdutosGrupo(grupoId) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/vinculos-produtos`);
  return data;
}

export async function vincularProdutosGrupo(grupoId, produtoA, produtoB) {
  const { data } = await api.post(`/grupos-empresas/${grupoId}/vinculos-produtos`, {
    produto_a: produtoA,
    produto_b: produtoB,
  });
  return data;
}

export async function removerVinculoProdutosGrupo(grupoId, vinculoId) {
  const { data } = await api.delete(`/grupos-empresas/${grupoId}/vinculos-produtos/${vinculoId}`);
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

export async function listarEstoqueCompartilhadoGrupo(grupoId) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/estoque-compartilhado`);
  return data;
}

export async function buscarProdutosEstoqueCompartilhado(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-empresas/${grupoId}/estoque-compartilhado/produtos`, {
    params,
  });
  return data;
}

export async function compartilharEstoqueGrupo(
  grupoId,
  empresaConsumidoraId,
  produtoIds,
  acessoCatalogoCompleto = false,
) {
  const { data } = await api.post(`/grupos-empresas/${grupoId}/estoque-compartilhado`, {
    empresa_consumidora_id: empresaConsumidoraId,
    produto_ids: produtoIds,
    acesso_catalogo_completo: acessoCatalogoCompleto,
  });
  return data;
}

export async function atualizarAcessoCatalogoCompartilhado(
  grupoId,
  compartilhamentoId,
  acessoCatalogoCompleto,
) {
  const { data } = await api.patch(
    `/grupos-empresas/${grupoId}/estoque-compartilhado/${compartilhamentoId}/catalogo`,
    { acesso_catalogo_completo: acessoCatalogoCompleto },
  );
  return data;
}

export async function removerEstoqueCompartilhadoGrupo(grupoId, compartilhamentoId) {
  const { data } = await api.delete(
    `/grupos-empresas/${grupoId}/estoque-compartilhado/${compartilhamentoId}`,
  );
  return data;
}
