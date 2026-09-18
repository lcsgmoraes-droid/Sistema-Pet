import InputTexto from "../InputTexto/InputTexto";

export default function InputPercentual({
  disabled = false,
  error = "",
  help = "",
  id,
  label,
  maxValue = 100,
  name,
  onChange,
  required = false,
  value = 0,
}) {
  const centesimos = Math.round(Number(value || 0) * 100);
  const centesimosMax = Math.round(maxValue * 100);

  const display = `${(centesimos / 100).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}%`;

  const emitir = (novosCentesimos) => onChange?.(novosCentesimos / 100);

  const aoPressionarTecla = (evento) => {
    const tudoSelecionado =
      evento.target.selectionStart === 0 &&
      evento.target.selectionEnd === evento.target.value.length &&
      evento.target.value.length > 0;

    if (evento.key >= "0" && evento.key <= "9") {
      evento.preventDefault();
      const base = tudoSelecionado ? 0 : centesimos;
      emitir(Math.min(base * 10 + Number(evento.key), centesimosMax));
    } else if (evento.key === "Backspace") {
      evento.preventDefault();
      emitir(tudoSelecionado ? 0 : Math.floor(centesimos / 10));
    } else if (evento.key === "Delete") {
      evento.preventDefault();
      onChange?.(0);
    }
  };

  return (
    <InputTexto
      alinhamentoTexto="direita"
      disabled={disabled}
      error={error}
      help={help}
      id={id}
      inputMode="numeric"
      label={label}
      name={name}
      onChange={() => {}}
      onKeyDown={aoPressionarTecla}
      required={required}
      value={display}
    />
  );
}
