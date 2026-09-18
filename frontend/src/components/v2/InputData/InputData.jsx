import { Calendar } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import CalendarioPainel from "../CalendarioPainel/CalendarioPainel";
import InputTexto from "../InputTexto/InputTexto";
import { isoParaData } from "../utils/calendario";
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
  const containerRef = useRef(null);
  const [texto, setTexto] = useState(() => formatarDataDigitos(isoParaDigitosData(value)));
  const [aberto, setAberto] = useState(false);
  const [mesVisivel, setMesVisivel] = useState(() => isoParaData(value) || new Date());

  useEffect(() => {
    const digitosExternos = isoParaDigitosData(value);
    if (digitosExternos !== apenasDigitos(texto)) {
      setTexto(formatarDataDigitos(digitosExternos));
    }
  }, [value]);

  useEffect(() => {
    if (!aberto) return undefined;
    const aoClicarFora = (evento) => {
      if (!containerRef.current?.contains(evento.target)) setAberto(false);
    };
    document.addEventListener("mousedown", aoClicarFora);
    return () => document.removeEventListener("mousedown", aoClicarFora);
  }, [aberto]);

  const aoDigitar = (novoTexto) => {
    const digitos = apenasDigitos(novoTexto).slice(0, 8);
    setTexto(formatarDataDigitos(digitos));
    onChange?.(dataDigitosParaISO(digitos));
  };

  const aoSelecionarDia = (iso) => {
    setTexto(formatarDataDigitos(isoParaDigitosData(iso)));
    onChange?.(iso);
    setAberto(false);
  };

  return (
    <div ref={containerRef} className="relative w-full">
      <InputTexto
        disabled={disabled}
        error={error}
        help={help === undefined ? "dd/mm/aaaa" : help}
        id={id}
        inputMode="numeric"
        label={label}
        name={name}
        onChange={aoDigitar}
        onFocus={() => {
          if (isoParaData(value)) setMesVisivel(isoParaData(value));
          setAberto(true);
        }}
        placeholder="dd/mm/aaaa"
        required={required}
        right={
          <button
            type="button"
            tabIndex={-1}
            disabled={disabled}
            aria-label="Abrir calendário"
            onClick={() => setAberto((atual) => !atual)}
            className="rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:cursor-not-allowed dark:hover:bg-slate-800 dark:hover:text-slate-300"
          >
            <Calendar className="h-4 w-4" />
          </button>
        }
        value={texto}
      />
      {aberto ? (
        <CalendarioPainel
          mesVisivel={mesVisivel}
          onMudarMes={setMesVisivel}
          onSelecionarDia={aoSelecionarDia}
          selecionados={value ? [value] : []}
        />
      ) : null}
    </div>
  );
}
