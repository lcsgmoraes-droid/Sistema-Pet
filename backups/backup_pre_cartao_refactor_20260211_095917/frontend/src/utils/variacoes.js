/**
 * Utilitários para formatação de produtos com variações
 * Sprint 2 - Sistema Pet Shop Pro
 */

/**
 * Formata os atributos de uma variação para exibição
 * @param {Object} produto - Produto com variation_attributes
 * @returns {string} - String formatada (ex: "Cor: Azul | Tamanho: M")
 */
export function formatarVariacao(produto) {
  if (!produto) return '';
  
  // Se tiver variation_attributes (JSON)
  if (produto.variation_attributes && typeof produto.variation_attributes === 'object') {
    const atributos = Object.entries(produto.variation_attributes)
      .map(([chave, valor]) => {
        // Capitalizar primeira letra da chave
        const chaveFormatada = chave.charAt(0).toUpperCase() + chave.slice(1);
        return `${chaveFormatada}: ${valor}`;
      })
      .join(' | ');
    
    return atributos;
  }
  
  // Se tiver variation_signature (string)
  if (produto.variation_signature) {
    const atributos = produto.variation_signature
      .split('|')
      .map(part => {
        const [chave, valor] = part.split(':');
        if (chave && valor) {
          const chaveFormatada = chave.charAt(0).toUpperCase() + chave.slice(1);
          return `${chaveFormatada}: ${valor}`;
        }
        return part;
      })
      .join(' | ');
    
    return atributos;
  }
  
  return '';
}

/**
 * Gera o nome completo de uma variação para exibição
 * @param {Object} produto - Produto variação
 * @param {Object} produtoPai - Produto pai (opcional)
 * @returns {string} - Nome formatado
 */
export function nomeCompletoVariacao(produto, produtoPai = null) {
  if (!produto) return '';
  
  // Se for variação e tiver produto pai
  if (produto.tipo_produto === 'VARIACAO' && produtoPai) {
    const atributos = formatarVariacao(produto);
    if (atributos) {
      return `${produtoPai.nome} - ${atributos}`;
    }
    return produto.nome;
  }
  
  // Se for variação mas não temos o pai, tentar extrair da signature
  if (produto.tipo_produto === 'VARIACAO') {
    const atributos = formatarVariacao(produto);
    if (atributos) {
      return `${produto.nome.split(' - ')[0]} - ${atributos}`;
    }
  }
  
  return produto.nome;
}

/**
 * Verifica se um produto é vendável
 * @param {Object} produto - Produto a verificar
 * @returns {boolean}
 */
export function isProdutoVendavel(produto) {
  if (!produto) return false;
  
  // Produtos PAI não são vendáveis
  if (produto.is_parent || produto.tipo_produto === 'PAI') {
    return false;
  }
  
  // Produtos SIMPLES, VARIACAO e KIT são vendáveis
  return ['SIMPLES', 'VARIACAO', 'KIT'].includes(produto.tipo_produto);
}
