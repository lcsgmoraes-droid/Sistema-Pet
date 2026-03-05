/**
 * QuantidadeInput — campo de edição de quantidade para o PDV.
 *
 * Problema resolvido: input type="number" controla o valor em tempo real,
 * o que impede digitar "0.5871" (converte antes de terminar).
 *
 * Solução: exibe texto livre enquanto o usuário digita.
 * Só converte para número ao sair do campo (onBlur) ou pressionar Enter.
 *
 * Aceita vírgula ou ponto como separador decimal.
 * Permite apagar tudo e redigitar sem conflito.
 */
import { useState, useEffect } from 'react';

export default function QuantidadeInput({ value, onChange, disabled, className, min = 0.001 }) {
  const [display, setDisplay] = useState('');

  // Sincroniza quando o valor muda por fora (ex: botões + e -)
  useEffect(() => {
    setDisplay(value !== undefined && value !== null ? String(value) : '');
  }, [value]);

  const handleChange = (e) => {
    const raw = e.target.value;
    // Permite: dígitos, ponto ou vírgula (uma vez), sem outros caracteres
    if (raw === '' || /^[0-9]*[.,]?[0-9]*$/.test(raw)) {
      setDisplay(raw);
      // Atualiza em tempo real quando o valor é um número completo (não termina em . ou ,)
      if (raw !== '' && !/[.,]$/.test(raw)) {
        const normalized = raw.replace(',', '.');
        const num = parseFloat(normalized);
        if (!isNaN(num) && num > 0) {
          onChange(num);
        }
      }
    }
  };

  const commit = (raw) => {
    // Converte vírgula em ponto para parsear
    const normalized = raw.replace(',', '.');
    const num = parseFloat(normalized);
    const final = !isNaN(num) && num > 0 ? num : min;
    onChange(final);
    setDisplay(String(final));
  };

  const handleBlur = () => commit(display);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      e.target.blur();
    }
  };

  // Ao focar, seleciona tudo para facilitar substituição
  const handleFocus = (e) => e.target.select();

  return (
    <input
      type="text"
      inputMode="decimal"
      value={display}
      onChange={handleChange}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      onFocus={handleFocus}
      disabled={disabled}
      className={className}
    />
  );
}
