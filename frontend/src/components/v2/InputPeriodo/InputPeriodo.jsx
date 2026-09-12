import { Calendar } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import CalendarioIntervaloPainel from "../CalendarioIntervaloPainel/CalendarioIntervaloPainel";
import InputTexto from "../InputTexto/InputTexto";
import { isoParaData } from "../utils/calendario";
import { formatarDataDigitos, isoParaDigitosData } from "../utils/mascaras";

function formatarData(iso) {
  return formatarDataDigitos(isoParaDigitosData(iso));
}

export default function InputPeriodo({
  disabled = false,
  error = "",
  help = "Clique para escolher a data inicial e depois a final",
  id,
  label,
  onChange,
  required = false,
  value = {},
}) {
  const containerRef = useRef(null);
  const [aberto, setAberto] = useState(false);
  const [mesEsquerdo, setMesEsquerdo] = useState(() => isoParaData(value.inicio) || new Date());

  const { fim = "", inicio = "" } = value;

  useEffect(() => {
    if (!aberto) return undefined;
    const aoClicarFora = (evento) => {
      if (!containerRef.current?.contains(evento.target)) setAberto(false);
    };
    document.addEventListener("mousedown", aoClicarFora);
    return () => document.removeEventListener("mousedown", aoClicarFora);
  }, [aberto]);

  const abrir = () => {
    setMesEsquerdo(isoParaData(inicio) || new Date());
    setAberto(true);
  };

  const aoSelecionarDia = (iso) => {
    if (!inicio || (inicio && fim)) {
      onChange?.({ inicio: iso, fim: "" });
      return;
    }
    if (iso < inicio) {
      onChange?.({ inicio: iso, fim: inicio });
    } else {
      onChange?.({ inicio, fim: iso });
    }
    setAberto(false);
  };

  const textoExibido = inicio ? `${formatarData(inicio)} - ${fim ? formatarData(fim) : "..."}` : "";

  return (
    <div ref={containerRef} className="relative w-full">
      <InputTexto
        disabled={disabled}
        error={error}
        help={help}
        id={id}
        label={label}
        onFocus={abrir}
        placeholder="Selecione o período"
        readOnly
        required={required}
        right={
          <button
            type="button"
            tabIndex={-1}
            disabled={disabled}
            aria-label="Abrir calendário do período"
            onClick={() => (aberto ? setAberto(false) : abrir())}
            className="rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:cursor-not-allowed dark:hover:bg-slate-800 dark:hover:text-slate-300"
          >
            <Calendar className="h-4 w-4" />
          </button>
        }
        value={textoExibido}
      />
      {aberto ? (
        <CalendarioIntervaloPainel
          fim={fim}
          inicio={inicio}
          mesEsquerdo={mesEsquerdo}
          onMudarMesEsquerdo={setMesEsquerdo}
          onSelecionarDia={aoSelecionarDia}
        />
      ) : null}
    </div>
  );
}
