/**
 * CurrencyInput — campo monetário com máscara de preenchimento da direita.
 *
 * Comportamento:
 *   - Digitar "5"         → 0,05
 *   - Digitar "5" novamente → 0,55
 *   - Digitar "5" novamente → 5,55
 *   - Digitar em valores grandes → 1.234,56
 *   - Backspace           → volta um dígito
 *   - Delete              → zera o campo
 *
 * PADRÃO OBRIGATÓRIO: ponto como separador de milhar, vírgula como decimal.
 *   Exemplo: 17.555,25
 *
 * Props:
 *   value    (number)   — valor em reais (float), ex: 39.90
 *   onChange (function) — chamada com novo float quando muda
 *   maxValue (number)   — valor máximo permitido em reais (opcional)
 *   className (string)  — classes CSS extras
 *   ...rest             — demais props HTML para o input (autoFocus, id, etc.)
 */
export default function CurrencyInput({
  value,
  onChange,
  maxValue,
  allowNegative = false,
  className = "",
  ...rest
}) {
  const numericValue = Number(value || 0);
  const sign = allowNegative && numericValue < 0 ? -1 : 1;
  const cents = Math.round(Math.abs(numericValue) * 100);
  const maxCents = maxValue !== undefined ? Math.round(maxValue * 100) : 999999999;

  // Exibição com separador de milhar: 17.555,25
  const displayValue = (cents / 100).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const display = sign < 0 ? `-${displayValue}` : displayValue;

  const emitValue = (nextCents, nextSign = sign) => {
    const absoluteValue = nextCents / 100;
    onChange(nextSign < 0 && absoluteValue > 0 ? -absoluteValue : absoluteValue);
  };

  const handleKeyDown = (e) => {
    // Detectar se o campo está totalmente selecionado (Ctrl+A ou clique e arraste)
    const tudoSelecionado =
      e.target.selectionStart === 0 &&
      e.target.selectionEnd === e.target.value.length &&
      e.target.value.length > 0;

    if (e.key >= "0" && e.key <= "9") {
      e.preventDefault();
      // Se todo o conteúdo estava selecionado, começar do zero (substituir)
      const base = tudoSelecionado ? 0 : cents;
      const novo = Math.min(base * 10 + Number(e.key), maxCents);
      emitValue(novo);
    } else if (e.key === "Backspace") {
      e.preventDefault();
      // Se tudo selecionado, apagar tudo
      emitValue(tudoSelecionado ? 0 : Math.floor(cents / 10));
    } else if (e.key === "Delete") {
      e.preventDefault();
      onChange(0);
    } else if (allowNegative && e.key === "-") {
      e.preventDefault();
      emitValue(cents, sign < 0 ? 1 : -1);
    } else if (allowNegative && e.key === "+") {
      e.preventDefault();
      emitValue(cents, 1);
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
