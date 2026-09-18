import { Calendar } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import CalendarioPainel from "../CalendarioPainel/CalendarioPainel";
import InputTexto from "../InputTexto/InputTexto";
import { isoParaData } from "../utils/calendario";
import {
  apenasDigitos,
  dataHoraDigitosParaISO,
  formatarDataHoraDigitos,
  isoParaDigitosDataHora,
} from "../utils/mascaras";

const campoHoraClasse =
  "h-8 w-14 rounded-md border border-slate-300 bg-white px-2 text-center text-sm text-slate-900 outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500 dark:!border-slate-700 dark:!bg-slate-950 dark:!text-slate-100";

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
  const containerRef = useRef(null);
  const [texto, setTexto] = useState(() => formatarDataHoraDigitos(isoParaDigitosDataHora(value)));
  const [aberto, setAberto] = useState(false);
  const [mesVisivel, setMesVisivel] = useState(() => isoParaData(value) || new Date());

  useEffect(() => {
    const digitosExternos = isoParaDigitosDataHora(value);
    if (digitosExternos !== apenasDigitos(texto)) {
      setTexto(formatarDataHoraDigitos(digitosExternos));
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
    const digitos = apenasDigitos(novoTexto).slice(0, 12);
    setTexto(formatarDataHoraDigitos(digitos));
    onChange?.(dataHoraDigitosParaISO(digitos));
  };

  const digitosAtuais = apenasDigitos(texto);
  const horaAtual = digitosAtuais.slice(8, 10) || "00";
  const minutoAtual = digitosAtuais.slice(10, 12) || "00";

  const aplicarNovaDataHora = (dataDigitos, hora, minuto) => {
    const digitos = `${dataDigitos}${hora.padStart(2, "0")}${minuto.padStart(2, "0")}`;
    setTexto(formatarDataHoraDigitos(digitos));
    onChange?.(dataHoraDigitosParaISO(digitos));
  };

  const aoSelecionarDia = (iso) => {
    const dataDigitos = iso.slice(8, 10) + iso.slice(5, 7) + iso.slice(0, 4);
    aplicarNovaDataHora(dataDigitos, horaAtual, minutoAtual);
  };

  return (
    <div ref={containerRef} className="relative w-full">
      <InputTexto
        disabled={disabled}
        error={error}
        help={help === undefined ? "dd/mm/aaaa hh:mm" : help}
        id={id}
        inputMode="numeric"
        label={label}
        name={name}
        onChange={aoDigitar}
        onFocus={() => setAberto(true)}
        placeholder="dd/mm/aaaa hh:mm"
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
          selecionados={
            digitosAtuais.length >= 8
              ? [
                  `${digitosAtuais.slice(4, 8)}-${digitosAtuais.slice(2, 4)}-${digitosAtuais.slice(0, 2)}`,
                ]
              : []
          }
          rodape={
            <div className="flex items-center justify-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <span>Hora:</span>
              <input
                type="text"
                inputMode="numeric"
                maxLength={2}
                value={horaAtual}
                onChange={(evento) =>
                  aplicarNovaDataHora(
                    digitosAtuais.slice(0, 8),
                    apenasDigitos(evento.target.value).slice(0, 2),
                    minutoAtual,
                  )
                }
                className={campoHoraClasse}
              />
              <span>:</span>
              <input
                type="text"
                inputMode="numeric"
                maxLength={2}
                value={minutoAtual}
                onChange={(evento) =>
                  aplicarNovaDataHora(
                    digitosAtuais.slice(0, 8),
                    horaAtual,
                    apenasDigitos(evento.target.value).slice(0, 2),
                  )
                }
                className={campoHoraClasse}
              />
            </div>
          }
        />
      ) : null}
    </div>
  );
}
