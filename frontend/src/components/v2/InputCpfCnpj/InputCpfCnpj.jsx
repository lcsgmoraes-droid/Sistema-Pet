import InputTexto from "../InputTexto/InputTexto";
import { apenasDigitos, formatarCpfCnpjDigitos } from "../utils/mascaras";

export default function InputCpfCnpj({
  disabled = false,
  error = "",
  help = "",
  id,
  label = "CPF/CNPJ",
  name,
  onChange,
  required = false,
  value = "",
}) {
  const aoDigitar = (novoTexto) => {
    const digitos = apenasDigitos(novoTexto).slice(0, 14);
    onChange?.(formatarCpfCnpjDigitos(digitos));
  };

  return (
    <InputTexto
      disabled={disabled}
      error={error}
      help={help}
      id={id}
      inputMode="numeric"
      label={label}
      name={name}
      onChange={aoDigitar}
      placeholder="000.000.000-00"
      required={required}
      value={value}
    />
  );
}
