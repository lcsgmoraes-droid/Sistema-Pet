/**
 * Helper para conversão inteligente de idade
 * Aceita múltiplos formatos e sempre retorna meses
 */

/**
 * Converte data de nascimento para idade em meses
 * @param {Date|string} dataNascimento 
 * @returns {number} idade em meses
 */
export function calcularIdadeMeses(dataNascimento) {
  if (!dataNascimento) return null;
  
  const data = typeof dataNascimento === 'string' ? new Date(dataNascimento) : dataNascimento;
  const hoje = new Date();
  
  const anos = hoje.getFullYear() - data.getFullYear();
  const meses = hoje.getMonth() - data.getMonth();
  
  return (anos * 12) + meses;
}

/**
 * Converte idade em meses para anos (formatado)
 * @param {number} meses 
 * @returns {string} Ex: "2 anos e 3 meses" ou "10 meses" ou "1 ano"
 */
export function formatarIdadeMeses(meses) {
  if (!meses) return '-';
  
  const anos = Math.floor(meses / 12);
  const mesesRestantes = meses % 12;
  
  if (anos === 0) {
    return `${meses} ${meses === 1 ? 'mês' : 'meses'}`;
  }
  
  if (mesesRestantes === 0) {
    return `${anos} ${anos === 1 ? 'ano' : 'anos'}`;
  }
  
  return `${anos} ${anos === 1 ? 'ano' : 'anos'} e ${mesesRestantes} ${mesesRestantes === 1 ? 'mês' : 'meses'}`;
}

/**
 * Converte entrada de texto em meses
 * Aceita formatos:
 * - "13 anos" → 156
 * - "2 anos e 3 meses" → 27
 * - "10 meses" → 10
 * - "1.5 anos" ou "1,5 anos" → 18
 * - "24" (número) → 24
 * 
 * @param {string} texto 
 * @returns {number|null} idade em meses ou null se inválido
 */
export function parseIdadeParaMeses(texto) {
  if (!texto) return null;
  
  const textoLimpo = texto.toString().toLowerCase().trim();
  
  // Se for apenas número, considera meses
  if (/^\d+$/.test(textoLimpo)) {
    return parseInt(textoLimpo);
  }
  
  // Padrão: "X anos e Y meses" ou variações
  const regexAnosMeses = /(\d+(?:[.,]\d+)?)\s*anos?\s*(?:e\s*)?(\d+)?\s*meses?/i;
  const matchAnosMeses = textoLimpo.match(regexAnosMeses);
  
  if (matchAnosMeses) {
    const anos = parseFloat(matchAnosMeses[1].replace(',', '.'));
    const meses = matchAnosMeses[2] ? parseInt(matchAnosMeses[2]) : 0;
    return Math.round(anos * 12) + meses;
  }
  
  // Padrão: apenas anos (com ou sem decimal)
  const regexAnos = /(\d+(?:[.,]\d+)?)\s*anos?/i;
  const matchAnos = textoLimpo.match(regexAnos);
  
  if (matchAnos) {
    const anos = parseFloat(matchAnos[1].replace(',', '.'));
    return Math.round(anos * 12);
  }
  
  // Padrão: apenas meses
  const regexMeses = /(\d+)\s*meses?/i;
  const matchMeses = textoLimpo.match(regexMeses);
  
  if (matchMeses) {
    return parseInt(matchMeses[1]);
  }
  
  return null;
}

/**
 * Valida se o texto pode ser convertido em idade
 * @param {string} texto 
 * @returns {boolean}
 */
export function validarIdadeTexto(texto) {
  return parseIdadeParaMeses(texto) !== null;
}

/**
 * Gera placeholder para campo de idade
 * @returns {string}
 */
export function getPlaceholderIdade() {
  return 'Ex: 2 anos, 10 meses, 1.5 anos, 2 anos e 3 meses';
}

/**
 * Formata valor do campo para exibição amigável
 * Se for número puro de meses, converte para formato legível
 * @param {number|string} valor 
 * @returns {string}
 */
export function formatarCampoIdade(valor) {
  if (!valor) return '';
  
  // Se for número, formatar
  if (typeof valor === 'number' || /^\d+$/.test(valor)) {
    return formatarIdadeMeses(parseInt(valor));
  }
  
  // Se já for texto formatado, retornar como está
  return valor;
}
