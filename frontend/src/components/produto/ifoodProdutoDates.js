// O formulário usa o relógio local do usuário; a API recebe um instante UTC.
// A conversão fica restrita ao iFood para preservar os canais já existentes.
export function serializarDataHoraIfood(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

export function dataHoraIfoodParaFormulario(value) {
  if (!value) return "";
  const text = String(value);
  // Compatibilidade com datas antigas do servidor sem offset, tratadas em UTC.
  const iso = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(text) ? text : `${text}Z`;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
