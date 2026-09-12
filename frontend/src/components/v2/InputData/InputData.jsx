import { useEffect, useState } from "react";
import InputTexto from "../InputTexto/InputTexto";
import {
  apenasDigitos,
  dataDigitosParaISO,
  formatarDataDigitos,
  isoParaDigitosData,
} from "../utils/mascaras";

export default function InputData({
  disabled = false,
  error = "",
  help,
  id,
  label,
  name,
  onChange,
  required = false,
  value = "",
}) {
  const [texto, setTexto] = useState(() => formatarDataDigitos(isoParaDigitosData(value)));

  useEffect(() => {
    const digitosExternos = isoParaDigitosData(value);
    if (digitosExternos !== apenasDigitos(texto)) {
      setTexto(formatarDataDigitos(digitosExternos));
    }
  }, [value]);

  const aoDigitar = (novoTexto) => {
    const digitos = apenasDigitos(novoTexto).slice(0, 8);
    setTexto(formatarDataDigitos(digitos));
    onChange?.(dataDigitosParaISO(digitos));
  };

  return (
    <InputTexto
      disabled={disabled}
      error={error}
      help={help === undefined ? "dd/mm/aaaa" : help}
      id={id}
      inputMode="numeric"
      label={label}
      name={name}
      onChange={aoDigitar}
      placeholder="dd/mm/aaaa"
      required={required}
      value={texto}
    />
  );
}
