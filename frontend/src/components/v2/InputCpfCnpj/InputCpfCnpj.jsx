import InputTexto from "../InputTexto/InputTexto";
import { formatarDocumento } from "../utils/mascaras";

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
  return (
    <InputTexto
      disabled={disabled}
      error={error}
      help={help}
      id={id}
      label={label}
      name={name}
      onChange={(novoTexto) => onChange?.(formatarDocumento(novoTexto))}
      placeholder="000.000.000-00"
      required={required}
      value={value}
    />
  );
}
