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

export function formatarCpfCnpjDigitos(digitos) {
  const numero = digitos.slice(0, 14);
  if (numero.length <= 11) {
    return numero
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
  }
  return numero
    .replace(/(\d{2})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1/$2")
    .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
}

export function tipoDocumento(digitos) {
  if (digitos.length > 11) return "cnpj";
  return "cpf";
}
