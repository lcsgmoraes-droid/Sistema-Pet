export const MAX_DASHBOARD_PERIOD_DAYS = 90;

function dataISOValida(value) {
  if (typeof value !== "string" || !/^(?!0000)\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const data = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(data.getTime()) && data.toISOString().slice(0, 10) === value;
}

export function validarPeriodoDashboard({ inicio, fim } = {}) {
  if (!inicio || !fim) return { erro: "Escolha a data inicial e a data final." };
  if (!dataISOValida(inicio) || !dataISOValida(fim)) return { erro: "Informe datas válidas." };
  if (fim < inicio) return { erro: "A data final deve ser igual ou posterior à inicial." };
  const dias = (Date.parse(fim) - Date.parse(inicio)) / 86400000 + 1;
  if (dias > MAX_DASHBOARD_PERIOD_DAYS) {
    return { erro: `Escolha um período de até ${MAX_DASHBOARD_PERIOD_DAYS} dias.` };
  }
  return { erro: "", dias };
}

export function chavePeriodoDashboard(periodo) {
  return periodo.inicio ? `datas:${periodo.inicio}:${periodo.fim}` : `dias:${periodo.dias}`;
}

export function parametrosPeriodoDashboard(periodo) {
  return periodo.inicio
    ? { data_inicio: periodo.inicio, data_fim: periodo.fim }
    : { periodo_dias: periodo.dias };
}

export function rotuloPeriodoDashboard(periodo) {
  const formatar = (data) => data.split("-").reverse().join("/");
  return periodo.inicio
    ? `${formatar(periodo.inicio)} a ${formatar(periodo.fim)}`
    : Number(periodo.dias) === 1
      ? "Hoje"
      : `Últimos ${periodo.dias} dias`;
}
