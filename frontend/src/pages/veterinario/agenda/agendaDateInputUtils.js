export function mascararDataBr(valor) {
  const digitos = String(valor || "")
    .replace(/\D/g, "")
    .slice(0, 8);

  if (digitos.length <= 2) return digitos;
  if (digitos.length <= 4) return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;

  return `${digitos.slice(0, 2)}/${digitos.slice(2, 4)}/${digitos.slice(4)}`;
}

export function parseDataBrParaIso(valor) {
  const match = String(valor || "")
    .trim()
    .match(/^(\d{2})\/(\d{2})\/(\d{4})$/);

  if (!match) return "";

  const [, dia, mes, ano] = match;
  if (!dataValida({ dia, mes, ano })) return "";

  return `${ano}-${mes}-${dia}`;
}

export function formatarDataIsoParaBr(valor) {
  const match = String(valor || "")
    .trim()
    .match(/^(\d{4})-(\d{2})-(\d{2})$/);

  if (!match) return "";

  const [, ano, mes, dia] = match;
  if (!dataValida({ dia, mes, ano })) return "";

  return `${dia}/${mes}/${ano}`;
}

function dataValida({ dia, mes, ano }) {
  const diaNumero = Number(dia);
  const mesNumero = Number(mes);
  const anoNumero = Number(ano);

  if (
    !Number.isInteger(diaNumero) ||
    !Number.isInteger(mesNumero) ||
    !Number.isInteger(anoNumero)
  ) {
    return false;
  }

  if (ano.length !== 4 || mes.length !== 2 || dia.length !== 2) return false;
  if (anoNumero < 1900 || anoNumero > 2100) return false;
  if (mesNumero < 1 || mesNumero > 12) return false;

  const diasPorMes = [31, anoBissexto(anoNumero) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return diaNumero >= 1 && diaNumero <= diasPorMes[mesNumero - 1];
}

function anoBissexto(ano) {
  return ano % 4 === 0 && (ano % 100 !== 0 || ano % 400 === 0);
}
