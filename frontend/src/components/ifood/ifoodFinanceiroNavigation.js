const DIA_MS = 24 * 60 * 60 * 1000;

function diaIso(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  if (Number(value.slice(0, 4)) < 1) return null;
  const data = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(data.getTime()) && data.toISOString().slice(0, 10) === value
    ? data.getTime()
    : null;
}

export function periodoFinanceiroValido(periodo) {
  const inicio = diaIso(periodo?.inicio);
  const fim = diaIso(periodo?.fim);
  if (inicio === null || fim === null) return false;
  const dias = (fim - inicio) / DIA_MS + 1;
  return dias >= 1 && dias <= 33;
}

// Apenas sugere a apresentação inicial. A URL não concede acesso nem sincroniza eventos.
export function lerLinkFinanceiro(search = "") {
  const params = new URLSearchParams(search);
  if (params.get("aba") !== "financeiro") return null;
  const periodo = { inicio: params.get("inicio"), fim: params.get("fim") };
  return periodoFinanceiroValido(periodo) ? periodo : null;
}
