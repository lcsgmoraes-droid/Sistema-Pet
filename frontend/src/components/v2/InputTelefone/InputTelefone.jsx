import InputTexto from "../InputTexto/InputTexto";
import { apenasDigitos, formatarTelefoneDigitos } from "../utils/mascaras";

export default function InputTelefone({
  disabled = false,
  error = "",
  help = "",
  id,
  label,
  name,
  onChange,
  required = false,
  value = "",
}) {
  const aoDigitar = (novoTexto) => {
    const digitos = apenasDigitos(novoTexto).slice(0, 11);
    onChange?.(formatarTelefoneDigitos(digitos));
  };

  return (
    <InputTexto
      disabled={disabled}
      error={error}
      help={help}
      id={id}
      inputMode="tel"
      label={label}
      name={name}
      onChange={aoDigitar}
      placeholder="(00) 00000-0000"
      required={required}
      value={value}
    />
  );
}
