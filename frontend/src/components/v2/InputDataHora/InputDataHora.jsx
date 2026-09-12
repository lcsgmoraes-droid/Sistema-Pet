import { useEffect, useState } from "react";
import InputTexto from "../InputTexto/InputTexto";
import {
  apenasDigitos,
  dataHoraDigitosParaISO,
  formatarDataHoraDigitos,
  isoParaDigitosDataHora,
} from "../utils/mascaras";

export default function InputDataHora({
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
  const [texto, setTexto] = useState(() => formatarDataHoraDigitos(isoParaDigitosDataHora(value)));

  useEffect(() => {
    const digitosExternos = isoParaDigitosDataHora(value);
    if (digitosExternos !== apenasDigitos(texto)) {
      setTexto(formatarDataHoraDigitos(digitosExternos));
    }
  }, [value]);

  const aoDigitar = (novoTexto) => {
    const digitos = apenasDigitos(novoTexto).slice(0, 12);
    setTexto(formatarDataHoraDigitos(digitos));
    onChange?.(dataHoraDigitosParaISO(digitos));
  };

  return (
    <InputTexto
      disabled={disabled}
      error={error}
      help={help === undefined ? "dd/mm/aaaa hh:mm" : help}
      id={id}
      inputMode="numeric"
      label={label}
      name={name}
      onChange={aoDigitar}
      placeholder="dd/mm/aaaa hh:mm"
      required={required}
      value={texto}
    />
  );
}
