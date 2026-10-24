export function dataFinanceira(value) {
  if (!value) return "Não informado";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value.split("-").reverse().join("/");
  const data = new Date(value);
  return Number.isNaN(data.getTime())
    ? "Não informado"
    : data.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

export function periodoFinanceiroHoje() {
  const partes = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const parte = (tipo) => partes.find((item) => item.type === tipo)?.value;
  const dia = `${parte("year")}-${parte("month")}-${parte("day")}`;
  return { inicio: dia, fim: dia };
}

export function competenciaValida(value) {
  return typeof value === "string" && /^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(value);
}

export function competenciaFinanceira(value) {
  return competenciaValida(value)
    ? `${value.slice(5)}/${value.slice(0, 4)}`
    : value || "Não informada";
}
