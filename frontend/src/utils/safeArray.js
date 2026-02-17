/**
 * 🛡️ Helper para garantir que um valor seja sempre um array
 * Elimina erros do tipo ".map is not a function"
 * 
 * @param {*} value - Valor a ser verificado
 * @returns {Array} - Array seguro (original se for array, vazio se não for)
 */
export const safeArray = (value) => Array.isArray(value) ? value : [];

/**
 * 🛡️ Helper para acessar arrays aninhados com segurança
 * Ex: safeNestedArray(response, 'data', 'items')
 * 
 * @param {Object} obj - Objeto para navegar
 * @param  {...string} path - Caminho para o array
 * @returns {Array} - Array seguro
 */
export const safeNestedArray = (obj, ...path) => {
  let current = obj;
  for (const key of path) {
    current = current?.[key];
    if (current === undefined || current === null) return [];
  }
  return safeArray(current);
};
