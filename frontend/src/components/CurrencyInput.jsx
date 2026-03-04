/**
 * CurrencyInput — campo monetário com máscara de preenchimento da direita.
 *
 * Comportamento:
 *   - Digitar "5"         → R$ 0,05
 *   - Digitar "5" novamente → R$ 0,55
 *   - Digitar "5" novamente → R$ 5,55
 *   - Backspace           → volta um dígito
 *   - Delete              → zera o campo
 *
 * Props:
 *   value    (number)   — valor em reais (float), ex: 39.90
 *   onChange (function) — chamada com novo float quando muda
 *   maxValue (number)   — valor máximo permitido em reais (opcional)
 *   className (string)  — classes CSS extras
 *   ...rest             — demais props HTML para o input (autoFocus, id, etc.)
 */
export default function CurrencyInput({ value, onChange, maxValue, className = '', ...rest }) {
  const cents = Math.round((value || 0) * 100);
  const maxCents = maxValue !== undefined ? Math.round(maxValue * 100) : 999999999;

  // Exibição: se valor for zero mostra vazio (placeholder cuida disso)
  const display = cents > 0
    ? (cents / 100).toFixed(2).replace('.', ',')
    : '';

  const handleKeyDown = (e) => {
    if (e.key >= '0' && e.key <= '9') {
      e.preventDefault();
      const novo = Math.min(cents * 10 + Number(e.key), maxCents);
      onChange(novo / 100);
    } else if (e.key === 'Backspace') {
      e.preventDefault();
      onChange(Math.floor(cents / 10) / 100);
    } else if (e.key === 'Delete') {
      e.preventDefault();
      onChange(0);
    }
    // Todas as outras teclas (Tab, Enter, setas) passam normalmente
  };

  return (
    <input
      type="text"
      inputMode="numeric"
      value={display}
      onChange={() => {}} // controlado via onKeyDown
      onKeyDown={handleKeyDown}
      className={className}
      {...rest}
    />
  );
}
