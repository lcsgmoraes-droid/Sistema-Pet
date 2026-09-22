import { useEffect } from "react";
import { FaWhatsapp } from "react-icons/fa";
import InputTexto from "../InputTexto/InputTexto";
import { apenasDigitos, formatarTelefoneDigitos } from "../utils/mascaras";

const MAX_DIGITOS_POR_TIPO = {
  celular: 11,
  fixo: 10,
  ambos: 11,
};

const PLACEHOLDER_POR_TIPO = {
  celular: "(00) 00000-0000",
  fixo: "(00) 0000-0000",
  ambos: "(00) 00000-0000",
};

// Um único componente para celular e telefone fixo — a prop `tipo` decide o limite de dígitos e a
// máscara ("celular": 11 dígitos, "fixo": 10, "ambos": detecta pela quantidade digitada). O
// indicador de WhatsApp vem sempre embutido no próprio campo (nunca como um controle à parte na
// tela): fica habilitado só quando o número em questão é um celular — por `tipo="celular"` ou,
// em `tipo="ambos"`, assim que o usuário completa os 11 dígitos. Para telefone fixo o indicador
// fica travado em "não é WhatsApp", porque uma linha fixa não tem WhatsApp.
export default function InputTelefone({
  disabled = false,
  error = "",
  help = "",
  id,
  label,
  name,
  onChange,
  onChangeWhatsapp,
  required = false,
  tipo = "ambos",
  value = "",
  whatsapp = false,
}) {
  const maxDigitos = MAX_DIGITOS_POR_TIPO[tipo] || MAX_DIGITOS_POR_TIPO.ambos;

  const aoDigitar = (novoTexto) => {
    const digitos = apenasDigitos(novoTexto).slice(0, maxDigitos);
    onChange?.(formatarTelefoneDigitos(digitos));
  };

  const ehCelular =
    tipo === "celular" ? true : tipo === "fixo" ? false : apenasDigitos(value).length === 11;
  const whatsappHabilitado = !disabled && ehCelular;

  useEffect(() => {
    if (!whatsappHabilitado && whatsapp) onChangeWhatsapp?.(false);
  }, [whatsappHabilitado]);

  const whatsappMarcado = whatsappHabilitado && whatsapp;

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
      placeholder={PLACEHOLDER_POR_TIPO[tipo] || PLACEHOLDER_POR_TIPO.ambos}
      required={required}
      value={value}
      right={
        <button
          type="button"
          disabled={!whatsappHabilitado}
          aria-pressed={whatsappMarcado}
          aria-label={
            !whatsappHabilitado
              ? "WhatsApp não se aplica a telefone fixo"
              : whatsappMarcado
                ? "Marcado como WhatsApp — clique para desmarcar"
                : "Marcar como WhatsApp"
          }
          title={
            !whatsappHabilitado
              ? "Somente para celular"
              : whatsappMarcado
                ? "É WhatsApp"
                : "Não é WhatsApp"
          }
          onClick={() => onChangeWhatsapp?.(!whatsapp)}
          className={[
            "flex items-center rounded-md p-1 transition-colors",
            !whatsappHabilitado
              ? "cursor-not-allowed text-slate-300 dark:text-slate-600"
              : whatsappMarcado
                ? "bg-green-100 text-green-600 dark:bg-green-500/20 dark:text-green-400"
                : "text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300",
          ].join(" ")}
        >
          <FaWhatsapp className="h-4 w-4" aria-hidden="true" />
        </button>
      }
    />
  );
}
