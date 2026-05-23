function pad2(value) {
  return String(value).padStart(2, "0");
}

function formatarDateLocal(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return "-";
  }

  return [
    `${pad2(date.getDate())}/${pad2(date.getMonth() + 1)}/${date.getFullYear()}`,
    `${pad2(date.getHours())}:${pad2(date.getMinutes())}`,
  ].join(", ");
}

export function formatarDataHoraComissao(valor) {
  if (!valor) return "-";

  const texto = String(valor).trim();
  const temTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(texto);

  if (temTimezone) {
    return formatarDateLocal(new Date(texto));
  }

  const match = texto.match(
    /^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?)?/,
  );

  if (!match) {
    return formatarDateLocal(new Date(texto));
  }

  const [, ano, mes, dia, hora, minuto] = match;
  const data = `${dia}/${mes}/${ano}`;

  if (!hora || !minuto) {
    return data;
  }

  return `${data}, ${hora}:${minuto}`;
}
