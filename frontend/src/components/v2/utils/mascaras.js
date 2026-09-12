export function apenasDigitos(valor) {
  return String(valor ?? "").replace(/\D/g, "");
}

export function formatarDataDigitos(digitos) {
  const dia = digitos.slice(0, 2);
  const mes = digitos.slice(2, 4);
  const ano = digitos.slice(4, 8);
  let saida = dia;
  if (mes) saida += `/${mes}`;
  if (ano) saida += `/${ano}`;
  return saida;
}

export function formatarDataHoraDigitos(digitos) {
  const dataDigitos = digitos.slice(0, 8);
  const horaDigitos = digitos.slice(8, 12);
  let saida = formatarDataDigitos(dataDigitos);
  if (horaDigitos) {
    const hh = horaDigitos.slice(0, 2);
    const mm = horaDigitos.slice(2, 4);
    saida += ` ${hh}${mm ? `:${mm}` : ""}`;
  }
  return saida;
}

function dataValida(dia, mes, ano) {
  if (mes < 1 || mes > 12 || dia < 1 || ano < 1000) return false;
  const diasNoMes = new Date(ano, mes, 0).getDate();
  return dia <= diasNoMes;
}

export function dataDigitosParaISO(digitos) {
  if (digitos.length !== 8) return "";
  const dia = Number(digitos.slice(0, 2));
  const mes = Number(digitos.slice(2, 4));
  const ano = Number(digitos.slice(4, 8));
  if (!dataValida(dia, mes, ano)) return "";
  return `${digitos.slice(4, 8)}-${digitos.slice(2, 4)}-${digitos.slice(0, 2)}`;
}

export function isoParaDigitosData(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
  if (!match) return "";
  const [, ano, mes, dia] = match;
  return `${dia}${mes}${ano}`;
}

export function dataHoraDigitosParaISO(digitos) {
  if (digitos.length < 8) return "";
  const dataISO = dataDigitosParaISO(digitos.slice(0, 8));
  if (!dataISO) return "";
  if (digitos.length === 8) return `${dataISO}T00:00`;
  const horaDigitos = digitos.slice(8, 12).padEnd(4, "0");
  const hh = Number(horaDigitos.slice(0, 2));
  const mm = Number(horaDigitos.slice(2, 4));
  if (hh > 23 || mm > 59) return "";
  return `${dataISO}T${horaDigitos.slice(0, 2)}:${horaDigitos.slice(2, 4)}`;
}

export function isoParaDigitosDataHora(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(String(iso || ""));
  if (!match) return isoParaDigitosData(iso);
  const [, ano, mes, dia, hh, mm] = match;
  return `${dia}${mes}${ano}${hh}${mm}`;
}

export function formatarTelefoneDigitos(digitos) {
  const numero = digitos.slice(0, 11);
  if (numero.length <= 2) return numero ? `(${numero}` : "";
  if (numero.length <= 6) return `(${numero.slice(0, 2)}) ${numero.slice(2)}`;
  if (numero.length <= 10) {
    return `(${numero.slice(0, 2)}) ${numero.slice(2, 6)}-${numero.slice(6)}`;
  }
  return `(${numero.slice(0, 2)}) ${numero.slice(2, 7)}-${numero.slice(7)}`;
}

function formatarCpfDigitos(digitos) {
  const a = digitos.slice(0, 3);
  const b = digitos.slice(3, 6);
  const c = digitos.slice(6, 9);
  const d = digitos.slice(9, 11);
  let saida = a;
  if (b) saida += `.${b}`;
  if (c) saida += `.${c}`;
  if (d) saida += `-${d}`;
  return saida;
}

function formatarCnpjAlfanumerico(caracteres) {
  const a = caracteres.slice(0, 2);
  const b = caracteres.slice(2, 5);
  const c = caracteres.slice(5, 8);
  const d = caracteres.slice(8, 12);
  const e = caracteres.slice(12, 14);
  let saida = a;
  if (b) saida += `.${b}`;
  if (c) saida += `.${c}`;
  if (d) saida += `/${d}`;
  if (e) saida += `-${e}`;
  return saida;
}

// CNPJ, a partir de 2026 (Nota Tecnica COTEC/RFB), aceita letras nas 12
// primeiras posicoes (base + ordem) - só os 2 digitos verificadores finais
// continuam sendo sempre numericos. CPF permanece 100% numerico.
export function extrairDocumento(bruto) {
  const limpo = String(bruto || "")
    .toUpperCase()
    .replace(/[^0-9A-Z]/g, "");
  const contemLetra = /[A-Z]/.test(limpo);

  if (!contemLetra && limpo.length <= 11) {
    return { tipo: "cpf", valor: limpo };
  }

  const base = limpo.slice(0, 12);
  const digitosVerificadores = limpo
    .slice(12)
    .replace(/[^0-9]/g, "")
    .slice(0, 2);
  return { tipo: "cnpj", valor: `${base}${digitosVerificadores}`.slice(0, 14) };
}

export function formatarDocumento(bruto) {
  const { tipo, valor } = extrairDocumento(bruto);
  return tipo === "cpf" ? formatarCpfDigitos(valor) : formatarCnpjAlfanumerico(valor);
}
