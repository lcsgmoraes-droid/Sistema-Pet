/**
 * Utilitários de formatação — Padrão brasileiro (pt-BR)
 *
 * REGRA DO SISTEMA: Sempre usar estas funções para exibir valores monetários.
 * Formato obrigatório: ponto como separador de milhar, vírgula como decimal.
 * Exemplos:
 *   1234.5   → "1.234,50"
 *   17555.25 → "17.555,25"
 *   0.99     → "0,99"
 */

/**
 * Formata um número como moeda brasileira (sem prefixo R$).
 * @param {number} value
 * @returns {string}  ex: "17.555,25"
 */
export function formatBRL(value) {
  const num = parseFloat(value) || 0;
  return num.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Formata com prefixo "R$".
 * @param {number} value
 * @returns {string}  ex: "R$ 17.555,25"
 */
export function formatMoneyBRL(value) {
  return `R$ ${formatBRL(value)}`;
}

/**
 * Formata porcentagem com 2 casas.
 * @param {number} value
 * @returns {string}  ex: "12,50%"
 */
export function formatPercent(value) {
  const num = parseFloat(value) || 0;
  return num.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }) + '%';
}
