/**
 * Helper para Detecção de Produtos de Ração
 * ==========================================
 * 
 * Centraliza a lógica de detecção de ração em um único lugar.
 * Reutilizável em PDV, Calculadora, Relatórios, etc.
 * 
 * REGRA ÚNICA:
 * Um produto é considerado "ração" se:
 * - Nome da categoria contém "ração" ou "racao" (case-insensitive)
 * - OU categoria_id === 5 (ID conhecida de ração no banco)
 */

/**
 * Verifica se um produto é ração
 * @param {Object} produto - Objeto produto com categoria_id e categoria_nome
 * @returns {boolean} true se é ração, false caso contrário
 */
export function ehRacao(produto) {
  if (!produto) return false;

  if (typeof produto.eh_racao === 'boolean') {
    return produto.eh_racao;
  }

  const tipo = (produto.tipo || '').toString().toLowerCase();
  if (tipo === 'ração' || tipo === 'racao') {
    return true;
  }

  // 🎯 REGRA PRINCIPAL: Produto com peso_embalagem > 0 é ração
  // (mesmo critério usado pela Calculadora de Ração antiga que funciona)
  if (produto.peso_embalagem && produto.peso_embalagem > 0) {
    return true;
  }

  // 🔄 FALLBACK: Se não tiver peso_embalagem, verificar classificação ou categoria
  const classificacao = produto.classificacao_racao?.toLowerCase() || '';
  const categoriaId = produto.categoria_id || produto.category_id;
  const nomeCategoria = produto.categoria_nome?.toLowerCase() || '';

  return (
    (classificacao &&
      classificacao !== 'não é ração' &&
      classificacao !== 'nao' &&
      classificacao !== 'não') ||
    nomeCategoria.includes('ração') ||
    nomeCategoria.includes('racao') ||
    categoriaId === 5 // ID da categoria de ração (ajustar conforme BD)
  );
}

/**
 * Filtra apenas produtos de ração de um array
 * @param {Array} itens - Array de itens (produtos do carrinho, etc)
 * @returns {Array} Array contendo apenas os itens que são ração
 */
export function filtrarRacoes(itens) {
  if (!Array.isArray(itens)) return [];
  return itens.filter(item => ehRacao(item));
}

/**
 * Obtém a última ração de um array de itens
 * @param {Array} itens - Array de itens (produtos do carrinho, etc)
 * @returns {Object|null} O último item que é ração, ou null se não houver
 */
export function obterUltimaRacao(itens) {
  const racoes = filtrarRacoes(itens);
  return racoes.length > 0 ? racoes[racoes.length - 1] : null;
}

/**
 * Conta quantas rações existem em um array de itens
 * @param {Array} itens - Array de itens
 * @returns {number} Quantidade de rações
 */
export function contarRacoes(itens) {
  return filtrarRacoes(itens).length;
}

export default {
  ehRacao,
  filtrarRacoes,
  obterUltimaRacao,
  contarRacoes
};
