/**
 * SubtotalInput — campo do subtotal do item no PDV.
 *
 * Permite duas formas de editar:
 * - Alterar a quantidade diretamente (pelo QuantidadeInput ao lado)
 * - Digitar o valor total aqui → a quantidade é calculada automaticamente
 *
 * Exemplo: produto a R$ 61,44/unidade, cliente comprou R$ 41,78
 *   → quantidade calculada: 41,78 / 61,44 = 0,680 unidades
 */
import { useState, useEffect } from 'react';

export default function SubtotalInput({ subtotal, precoUnitario, onQuantidadeChange, disabled }) {
  const [display, setDisplay] = useState('');

  // Sincroniza o display quando o subtotal muda por fora (ex: mudança de quantidade)
  useEffect(() => {
    const valor = subtotal ?? 0;
    setDisplay(valor.toFixed(2).replace('.', ','));
  }, [subtotal]);

  const handleFocus = (e) => {
    e.target.select();
  };

  const handleChange = (e) => {
    const raw = e.target.value;
    if (raw === '' || /^[0-9]*[.,]?[0-9]*$/.test(raw)) {
      setDisplay(raw);
    }
  };

  const commit = (raw) => {
    const normalized = raw.replace(',', '.');
    const valor = parseFloat(normalized);
    if (!isNaN(valor) && valor > 0 && precoUnitario > 0) {
      const novaQuantidade = Math.round((valor / precoUnitario) * 10000) / 10000;
      onQuantidadeChange(novaQuantidade);
    } else {
      // Restaura o valor atual se inválido
      setDisplay((subtotal ?? 0).toFixed(2).replace('.', ','));
    }
  };

  const handleBlur = () => commit(display);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      e.target.blur();
    }
    if (e.key === 'Escape') {
      setDisplay((subtotal ?? 0).toFixed(2).replace('.', ','));
      e.target.blur();
    }
  };

  if (disabled) {
    return (
      <div className="text-lg font-semibold text-gray-900 w-28 text-right">
        R$ {(subtotal ?? 0).toFixed(2).replace('.', ',')}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1" title="Digite o valor total para calcular a quantidade">
      <span className="text-gray-600 font-medium text-sm">R$</span>
      <input
        type="text"
        inputMode="decimal"
        value={display}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="w-24 text-lg font-semibold text-gray-900 text-right border border-transparent hover:border-blue-300 focus:border-blue-500 rounded px-1 focus:ring-1 focus:ring-blue-500 focus:outline-none cursor-text"
      />
    </div>
  );
}
