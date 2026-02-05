/**
 * API de Produtos - Integração com Backend
 */
import api from '../api';

// ========================================
// CATEGORIAS
// ========================================

/**
 * Listar categorias (com filtros opcionais)
 */
export const getCategorias = (params = {}) => {
  return api.get('/produtos/categorias', { params });
};

/**
 * Obter hierarquia completa de categorias (árvore)
 */
export const getCategoriaHierarquia = () => {
  return api.get('/produtos/categorias/hierarquia');
};

/**
 * Obter categoria por ID
 */
export const getCategoria = (id) => {
  return api.get(`/produtos/categorias/${id}`);
};

/**
 * Criar nova categoria
 */
export const createCategoria = (data) => {
  return api.post('/produtos/categorias', data);
};

/**
 * Atualizar categoria
 */
export const updateCategoria = (id, data) => {
  return api.put(`/produtos/categorias/${id}`, data);
};

/**
 * Excluir categoria (soft delete)
 */
export const deleteCategoria = (id) => {
  return api.delete(`/produtos/categorias/${id}`);
};

// ========================================
// MARCAS
// ========================================

/**
 * Listar marcas (com busca opcional)
 */
export const getMarcas = (params = {}) => {
  return api.get('/produtos/marcas', { params });
};

/**
 * Obter marca por ID
 */
export const getMarca = (id) => {
  return api.get(`/produtos/marcas/${id}`);
};

/**
 * Criar nova marca
 */
export const createMarca = (data) => {
  return api.post('/produtos/marcas', data);
};

/**
 * Atualizar marca
 */
export const updateMarca = (id, data) => {
  return api.put(`/produtos/marcas/${id}`, data);
};

/**
 * Excluir marca (soft delete)
 */
export const deleteMarca = (id) => {
  return api.delete(`/produtos/marcas/${id}`);
};

// ========================================
// DEPARTAMENTOS
// ========================================

/**
 * Listar departamentos
 */
export const getDepartamentos = (params = {}) => {
  return api.get('/produtos/departamentos', { params });
};

/**
 * Obter departamento por ID
 */
export const getDepartamento = (id) => {
  return api.get(`/produtos/departamentos/${id}`);
};

/**
 * Criar novo departamento
 */
export const createDepartamento = (data) => {
  return api.post('/produtos/departamentos', data);
};

/**
 * Atualizar departamento
 */
export const updateDepartamento = (id, data) => {
  return api.put(`/produtos/departamentos/${id}`, data);
};

/**
 * Excluir departamento (soft delete)
 */
export const deleteDepartamento = (id) => {
  return api.delete(`/produtos/departamentos/${id}`);
};

// ========================================
// PRODUTOS
// ========================================

/**
 * Listar produtos (com filtros)
 * @param {Object} params - Filtros: busca, categoria_id, marca_id, departamento_id, estoque_baixo, em_promocao
 */
export const getProdutos = (params = {}) => {
  return api.get('/produtos', { params });
};

/**
 * Listar produtos VENDÁVEIS (SIMPLES e VARIACAO)
 * Usado no PDV e carrinho de vendas
 * @param {Object} params - Filtros: busca, categoria_id, marca_id, etc
 */
export const getProdutosVendaveis = (params = {}) => {
  return api.get('/produtos/vendaveis', { params });
};

/**
 * Obter produto por ID
 */
export const getProduto = (id) => {
  return api.get(`/produtos/${id}`);
};

/**
 * Obter variações de um produto PAI
 * Sprint 2: Lazy load de variações
 */
export const getProdutoVariacoes = (produtoId) => {
  return api.get(`/produtos/${produtoId}/variacoes`);
};

/**
 * Listar variações excluídas (lixeira)
 */
export const getProdutoVariacoesExcluidas = (produtoId) => {
  return api.get(`/produtos/${produtoId}/variacoes/excluidas`);
};

/**
 * Restaurar variação excluída
 */
export const restaurarVariacao = (variacaoId) => {
  return api.patch(`/produtos/${variacaoId}/restaurar`);
};

/**
 * Excluir variação PERMANENTEMENTE
 */
export const excluirVariacaoPermanente = (variacaoId) => {
  return api.delete(`/produtos/${variacaoId}/permanente`);
};

/**
 * Criar novo produto
 */
export const createProduto = (data) => {
  return api.post('/produtos/', data);
};

/**
 * Atualizar produto
 */
export const updateProduto = (id, data) => {
  return api.put(`/produtos/${id}`, data);
};

/**
 * Excluir produto (soft delete)
 */
export const deleteProduto = (id) => {
  return api.delete(`/produtos/${id}`);
};

/**
 * Gerar SKU automático
 * @param {string} prefixo - Prefixo opcional para o SKU
 */
export const gerarSKU = (prefixo = '') => {
  return api.post('/produtos/gerar-sku', { prefixo });
};

// ========================================
// CÓDIGO DE BARRAS EAN-13
// ========================================

/**
 * Gerar código de barras EAN-13
 * @param {string} sku - SKU do produto
 */
export const gerarCodigoBarras = (sku) => {
  return api.post('/produtos/gerar-codigo-barras', { sku });
};

/**
 * Validar código de barras
 */
export const validarCodigoBarras = (codigo) => {
  return api.get(`/produtos/validar-codigo-barras/${codigo}`);
};

// ========================================
// LOTES E FIFO
// ========================================

/**
 * Listar lotes de um produto (ordenado por FIFO)
 */
export const getLotes = (produtoId) => {
  return api.get(`/produtos/${produtoId}/lotes`);
};

/**
 * Criar novo lote
 */
export const createLote = (produtoId, data) => {
  return api.post(`/produtos/${produtoId}/lotes`, data);
};

/**
 * Entrada de estoque (cria lote automaticamente)
 */
export const entradaEstoque = (produtoId, data) => {
  return api.post(`/produtos/${produtoId}/entrada`, data);
};

/**
 * Atualizar lote
 */
export const updateLote = (produtoId, loteId, data) => {
  return api.put(`/produtos/${produtoId}/lotes/${loteId}`, data);
};

/**
 * Excluir lote
 */
export const deleteLote = (produtoId, loteId) => {
  return api.delete(`/produtos/${produtoId}/lotes/${loteId}`);
};

/**
 * Saída de estoque com FIFO (consome lotes antigos primeiro)
 */
export const saidaFIFO = (produtoId, data) => {
  return api.post(`/produtos/${produtoId}/saida-fifo`, data);
};

// ========================================
// IMAGENS
// ========================================

/**
 * Upload de imagem de produto
 */
export const uploadImagemProduto = (produtoId, formData) => {
  return api.post(`/produtos/${produtoId}/imagens`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

/**
 * Excluir imagem
 */
export const deleteImagemProduto = (imagemId) => {
  return api.delete(`/produtos/imagens/${imagemId}`);
};

/**
 * Definir imagem principal
 */
export const setImagemPrincipal = (imagemId) => {
  return api.put(`/produtos/imagens/${imagemId}/principal`);
};

// ========================================
// FORNECEDORES DO PRODUTO
// ========================================

/**
 * Listar fornecedores de um produto
 */
export const getFornecedoresProduto = (produtoId) => {
  return api.get(`/produtos/${produtoId}/fornecedores`);
};

/**
 * Adicionar fornecedor ao produto
 */
export const addFornecedorProduto = (produtoId, data) => {
  return api.post(`/produtos/${produtoId}/fornecedores`, data);
};

/**
 * Atualizar fornecedor do produto
 */
export const updateFornecedorProduto = (id, data) => {
  return api.put(`/produtos/fornecedores/${id}`, data);
};

/**
 * Remover fornecedor do produto
 */
export const deleteFornecedorProduto = (id) => {
  return api.delete(`/produtos/fornecedores/${id}`);
};

// ========================================
// LISTAS DE PREÇO
// ========================================

/**
 * Listar listas de preço
 */
export const getListasPreco = () => {
  return api.get('/produtos/listas-preco');
};

/**
 * Criar lista de preço
 */
export const createListaPreco = (data) => {
  return api.post('/produtos/listas-preco', data);
};

/**
 * Obter produtos de uma lista de preço
 */
export const getProdutosListaPreco = (listaId) => {
  return api.get(`/produtos/listas-preco/${listaId}/produtos`);
};

/**
 * Adicionar produto a lista de preço
 */
export const addProdutoListaPreco = (listaId, produtoId, preco) => {
  return api.post(`/produtos/listas-preco/${listaId}/produtos`, {
    produto_id: produtoId,
    preco,
  });
};

// ========================================
// RELATÓRIOS
// ========================================

/**
 * Relatório de movimentações de estoque
 * @param {Object} params - Filtros: data_inicio, data_fim, produto_id, tipo_movimentacao
 */
export const getRelatorioMovimentacoes = (params = {}) => {
  return api.get('/produtos/relatorio/movimentacoes', { params });
};

/**
 * Relatório de estoque baixo
 */
export const getRelatorioEstoqueBaixo = () => {
  return api.get('/produtos/relatorio/estoque-baixo');
};

/**
 * Relatório de produtos mais vendidos
 * @param {Object} params - Filtros: data_inicio, data_fim, limit
 */
export const getRelatorioMaisVendidos = (params = {}) => {
  return api.get('/produtos/relatorio/mais-vendidos', { params });
};

/**
 * Relatório de validades próximas
 * @param {number} dias - Dias para considerar validade próxima
 */
export const getRelatorioValidadeProxima = (dias = 30) => {
  return api.get('/produtos/relatorio/validade-proxima', { params: { dias } });
};

// ========================================
// UTILITÁRIOS
// ========================================

/**
 * Calcular preço de venda com base no markup
 * @param {number} precoCusto - Preço de custo
 * @param {number} markup - Percentual de markup
 */
export const calcularPrecoVenda = (precoCusto, markup) => {
  return precoCusto * (1 + markup / 100);
};

/**
 * Calcular markup com base no preço de venda
 * @param {number} precoCusto - Preço de custo
 * @param {number} precoVenda - Preço de venda
 */
export const calcularMarkup = (precoCusto, precoVenda) => {
  if (!precoCusto || precoCusto === 0) return 0;
  return ((precoVenda - precoCusto) / precoCusto) * 100;
};

/**
 * Formatar moeda (BRL)
 */
export const formatarMoeda = (valor) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(valor || 0);
};

/**
 * Formatar data
 */
export const formatarData = (data) => {
  if (!data) return '-';
  return new Date(data).toLocaleDateString('pt-BR');
};

/**
 * Formatar data e hora
 */
export const formatarDataHora = (data) => {
  if (!data) return '-';
  return new Date(data).toLocaleString('pt-BR');
};

export default {
  // Categorias
  getCategorias,
  getCategoriaHierarquia,
  getCategoria,
  createCategoria,
  updateCategoria,
  deleteCategoria,
  // Marcas
  getMarcas,
  getMarca,
  createMarca,
  updateMarca,
  deleteMarca,
  // Departamentos
  getDepartamentos,
  getDepartamento,
  createDepartamento,
  updateDepartamento,
  deleteDepartamento,
  // Produtos
  getProdutos,
  getProduto,
  createProduto,
  updateProduto,
  deleteProduto,
  gerarSKU,
  // Código de Barras
  gerarCodigoBarras,
  validarCodigoBarras,
  // Lotes/FIFO
  getLotes,
  createLote,
  entradaEstoque,
  saidaFIFO,
  // Imagens
  uploadImagemProduto,
  deleteImagemProduto,
  setImagemPrincipal,
  // Fornecedores
  getFornecedoresProduto,
  addFornecedorProduto,
  updateFornecedorProduto,
  deleteFornecedorProduto,
  // Listas de Preço
  getListasPreco,
  createListaPreco,
  getProdutosListaPreco,
  addProdutoListaPreco,
  // Relatórios
  getRelatorioMovimentacoes,
  getRelatorioEstoqueBaixo,
  getRelatorioMaisVendidos,
  getRelatorioValidadeProxima,
  // Utilitários
  calcularPrecoVenda,
  calcularMarkup,
  formatarMoeda,
  formatarData,
  formatarDataHora,
};
