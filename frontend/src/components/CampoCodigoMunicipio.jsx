import { useId } from "react";

export default function CampoCodigoMunicipio({ value, onChange }) {
  const inputId = useId();
  const helpId = `${inputId}-ajuda`;

  return (
    <div>
      <label htmlFor={inputId} className="block text-sm font-medium text-gray-700 mb-1">
        Código IBGE do município
      </label>
      <input
        id={inputId}
        type="text"
        inputMode="numeric"
        value={value || ""}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 7))}
        maxLength="7"
        aria-describedby={helpId}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        placeholder="7 dígitos"
      />
      <p id={helpId} className="text-xs text-gray-500 mt-1">
        A busca pelo CEP preenche este código. Confira o município antes de informar manualmente.
      </p>
    </div>
  );
}
