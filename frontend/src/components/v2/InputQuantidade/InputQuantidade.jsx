import { useEffect, useState } from "react";
import InputTexto from "../InputTexto/InputTexto";

export default function InputQuantidade({
  disabled = false,
  error = "",
  help = "",
  id,
  label,
  min = 0.001,
  name,
  onChange,
  required = false,
  value,
}) {
  const [texto, setTexto] = useState("");

  useEffect(() => {
    setTexto(value !== undefined && value !== null ? String(value) : "");
  }, [value]);

  const aoDigitar = (bruto) => {
    if (bruto === "" || /^[0-9]*[.,]?[0-9]*$/.test(bruto)) {
      setTexto(bruto);
      if (bruto !== "" && !/[.,]$/.test(bruto)) {
        const numero = parseFloat(bruto.replace(",", "."));
        if (!Number.isNaN(numero) && numero > 0) {
          onChange?.(numero);
        }
      }
    }
  };

  const confirmar = (bruto) => {
    const numero = parseFloat(bruto.replace(",", "."));
    const final = !Number.isNaN(numero) && numero > 0 ? numero : min;
    onChange?.(final);
    setTexto(String(final));
  };

  return (
    <InputTexto
      alinhamentoTexto="direita"
      disabled={disabled}
      error={error}
      help={help}
      id={id}
      inputMode="decimal"
      label={label}
      name={name}
      onBlur={(evento) => confirmar(evento.target.value)}
      onChange={aoDigitar}
      onKeyDown={(evento) => {
        if (evento.key === "Enter") evento.currentTarget.blur();
      }}
      required={required}
      value={texto}
    />
  );
}
