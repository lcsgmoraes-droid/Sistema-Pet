import { api } from "./api";

export async function obterResumoGruposComerciais() {
  const { data } = await api.get("/grupos-comerciais/resumo");
  return data;
}

export async function obterVisaoConsolidadaGrupo(grupoId, periodoDias = 30) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/visao-consolidada`, {
    params: { periodo_dias: periodoDias },
  });
  return data;
}

export async function obterPedidosGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/pedidos`, { params });
  return data;
}

export async function obterProdutosVendidosGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/produtos-vendidos`, {
    params,
  });
  return data;
}

export async function obterPedidosCompraGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/pedidos-compra`, { params });
  return data;
}

export async function obterContasPagarGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/contas-pagar`, { params });
  return data;
}

export async function obterReposicaoInteligenteGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/reposicao-inteligente`, {
    params,
  });
  return data;
}

export async function obterAnaliseFinanceiraGrupo(grupoId) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/analise-financeira`);
  return data;
}

export async function buscarProdutosGrupo(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/produtos`, { params });
  return data;
}

export async function obterVinculosProdutosGrupo(grupoId) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/vinculos-produtos`);
  return data;
}

export async function vincularProdutosGrupo(grupoId, produtoA, produtoB) {
  const { data } = await api.post(`/grupos-comerciais/${grupoId}/vinculos-produtos`, {
    produto_a: produtoA,
    produto_b: produtoB,
  });
  return data;
}

export async function removerVinculoProdutosGrupo(grupoId, vinculoId) {
  const { data } = await api.delete(`/grupos-comerciais/${grupoId}/vinculos-produtos/${vinculoId}`);
  return data;
}

/**
 * Provisiona uma loja nova e ja anexa ao grupo, como membro — unica forma
 * de um grupo crescer hoje (nao existe mais convite entre empresas ja
 * independentes). Reaproveita o usuario logado, sem pedir e-mail novo.
 */
export async function adicionarLojaGrupo(grupoId, { nomeLoja, nomeAcesso, plan, organizationType } = {}) {
  const { data } = await api.post(`/grupos-comerciais/${grupoId}/lojas`, {
    nome_loja: nomeLoja,
    nome_acesso: nomeAcesso || undefined,
    plan: plan || undefined,
    organization_type: organizationType || undefined,
  });
  return data;
}

export async function removerEmpresaGrupo(grupoId, empresaId) {
  const { data } = await api.delete(
    `/grupos-comerciais/${grupoId}/membros/${encodeURIComponent(empresaId)}`,
  );
  return data;
}

export async function listarEstoqueCompartilhadoGrupo(grupoId) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/estoque-compartilhado`);
  return data;
}

export async function buscarProdutosEstoqueCompartilhado(grupoId, params = {}) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/estoque-compartilhado/produtos`, {
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
  const { data } = await api.post(`/grupos-comerciais/${grupoId}/estoque-compartilhado`, {
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
    `/grupos-comerciais/${grupoId}/estoque-compartilhado/${compartilhamentoId}/catalogo`,
    { acesso_catalogo_completo: acessoCatalogoCompleto },
  );
  return data;
}

export async function removerEstoqueCompartilhadoGrupo(grupoId, compartilhamentoId) {
  const { data } = await api.delete(
    `/grupos-comerciais/${grupoId}/estoque-compartilhado/${compartilhamentoId}`,
  );
  return data;
}

/**
 * Visão consolidada dos dados mestre do grupo (Checkpoint 5 da camada
 * geral — ver Documentacao/Dominio/Plano-Camada-Geral.md): produtos, pets,
 * pessoas e espécies/raças já compartilhados entre as lojas do grupo.
 */
export async function obterMestresGrupo(grupoId) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/mestres`);
  return data;
}

/**
 * Situação de cobrança (Asaas) de cada loja do grupo — cada loja continua
 * sendo cobrada de forma independente, isso só consolida a visão. Só quem
 * tem acesso de gestão do grupo (master ou gestor concedido) enxerga.
 */
export async function listarBillingGrupo(grupoId) {
  const { data } = await api.get(`/grupos-comerciais/${grupoId}/billing`);
  return data;
}

/**
 * Rebusca no Asaas a cobrança em aberto de UMA loja do grupo (ex.: link do
 * boleto expirado). Não gera uma cobrança nova, só atualiza a existente.
 */
export async function sincronizarBillingLojaGrupo(grupoId, tenantId) {
  const { data } = await api.post(
    `/grupos-comerciais/${grupoId}/lojas/${encodeURIComponent(tenantId)}/billing/sincronizar`,
  );
  return data;
}

