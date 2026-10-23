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
import { useRef, useState } from "react";
import CurrencyInput from "./CurrencyInput";
import { formatBRL } from "../utils/formatters";

export default function SubtotalInput({ subtotal, precoUnitario, onSubtotalChange, disabled }) {
  const [valorDigitado, setValorDigitado] = useState(subtotal ?? 0);
  const [editando, setEditando] = useState(false);
  const cancelarEdicaoRef = useRef(false);

  const handleFocus = (e) => {
    setValorDigitado(subtotal ?? 0);
    setEditando(true);
    cancelarEdicaoRef.current = false;
    e.target.select();
  };

  const handleBlur = () => {
    if (!cancelarEdicaoRef.current && valorDigitado > 0 && precoUnitario > 0) {
      onSubtotalChange(valorDigitado);
    }
    // O subtotal informado e preservado; somente o peso usa tres casas.
    setEditando(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      e.target.blur();
    }
    if (e.key === "Escape") {
      cancelarEdicaoRef.current = true;
      e.target.blur();
    }
  };

  if (disabled) {
    return (
      <div className="w-24 shrink-0 text-right text-lg font-semibold text-gray-900 sm:w-28">
        R$ {formatBRL(subtotal ?? 0)}
      </div>
    );
  }

  return (
    <div
      className="flex shrink-0 items-center gap-1"
      title="Digite o valor total para calcular a quantidade"
      onKeyDown={handleKeyDown}
    >
      <span className="text-gray-600 font-medium text-sm">R$</span>
      <CurrencyInput
        value={editando ? valorDigitado : subtotal}
        onChange={setValorDigitado}
        onFocus={handleFocus}
        onBlur={handleBlur}
        className="w-24 shrink-0 text-lg font-semibold text-gray-900 text-right border border-transparent hover:border-blue-300 focus:border-blue-500 rounded px-1 focus:ring-1 focus:ring-blue-500 focus:outline-none cursor-text"
      />
    </div>
  );
}
