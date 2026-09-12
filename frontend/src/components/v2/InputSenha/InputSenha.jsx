import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import InputTexto from "../InputTexto/InputTexto";

export default function InputSenha({
  autoComplete,
  autoFocus,
  disabled = false,
  error = "",
  help = "",
  id,
  label = "Senha",
  name,
  onBlur,
  onChange,
  placeholder = "••••••••",
  required = false,
  value = "",
}) {
  const [visivel, setVisivel] = useState(false);

  return (
    <InputTexto
      autoComplete={autoComplete}
      autoFocus={autoFocus}
      disabled={disabled}
      error={error}
      help={help}
      id={id}
      label={label}
      name={name}
      onBlur={onBlur}
      onChange={onChange}
      placeholder={placeholder}
      required={required}
      type={visivel ? "text" : "password"}
      value={value}
      right={
        <button
          type="button"
          onClick={() => setVisivel((atual) => !atual)}
          disabled={disabled}
          aria-label={visivel ? "Ocultar senha" : "Mostrar senha"}
          title={visivel ? "Ocultar senha" : "Mostrar senha"}
          className="rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:cursor-not-allowed dark:hover:bg-slate-800 dark:hover:text-slate-300"
        >
          {visivel ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      }
    />
  );
}
