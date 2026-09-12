import InputTexto from "../InputTexto/InputTexto";

export default function InputMoeda({
  allowNegative = false,
  disabled = false,
  error = "",
  help = "",
  id,
  label,
  maxValue,
  name,
  onChange,
  required = false,
  value = 0,
}) {
  const numericValue = Number(value || 0);
  const sinal = allowNegative && numericValue < 0 ? -1 : 1;
  const centavos = Math.round(Math.abs(numericValue) * 100);
  const centavosMax = maxValue !== undefined ? Math.round(maxValue * 100) : 999999999;

  const textoExibido = (centavos / 100).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const display = sinal < 0 ? `-${textoExibido}` : textoExibido;

  const emitir = (novosCentavos, novoSinal = sinal) => {
    const valorAbsoluto = novosCentavos / 100;
    onChange?.(novoSinal < 0 && valorAbsoluto > 0 ? -valorAbsoluto : valorAbsoluto);
  };

  const aoPressionarTecla = (evento) => {
    const tudoSelecionado =
      evento.target.selectionStart === 0 &&
      evento.target.selectionEnd === evento.target.value.length &&
      evento.target.value.length > 0;

    if (evento.key >= "0" && evento.key <= "9") {
      evento.preventDefault();
      const base = tudoSelecionado ? 0 : centavos;
      emitir(Math.min(base * 10 + Number(evento.key), centavosMax));
    } else if (evento.key === "Backspace") {
      evento.preventDefault();
      emitir(tudoSelecionado ? 0 : Math.floor(centavos / 10));
    } else if (evento.key === "Delete") {
      evento.preventDefault();
      onChange?.(0);
    } else if (allowNegative && evento.key === "-") {
      evento.preventDefault();
      emitir(centavos, sinal < 0 ? 1 : -1);
    } else if (allowNegative && evento.key === "+") {
      evento.preventDefault();
      emitir(centavos, 1);
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
