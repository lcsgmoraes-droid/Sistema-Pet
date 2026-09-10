const formatInteger = new Intl.NumberFormat("pt-BR");
export const formatSequence = (value) => formatInteger.format(value);
export const environmentName = (code) => (Number(code) === 1 ? "Produção" : "Homologação");

export function currentSequence(rows, serie, environment) {
  if (!/^[0-9]{1,3}$/.test(serie) || Number(serie) > 889) return null;
  return (
    rows.find(
      (row) =>
        Number(row.serie) === Number(serie) &&
        row.ambienteCodigo === Number(environment) &&
        row.modelo === 55,
    ) ?? {
      serie: String(Number(serie)),
      ambienteCodigo: Number(environment),
      modelo: 55,
      ultimoNumero: 0,
      proximoNumero: 1,
      nova: true,
    }
  );
}

export function prepareNumbering(rows, form) {
  if (!Array.isArray(rows)) return { error: "Consulte a numeração antes de ajustar." };
  if (!["1", "2"].includes(String(form.ambiente_codigo))) return { error: "Escolha o ambiente." };
  const current = currentSequence(rows, form.serie, form.ambiente_codigo);
  if (!current) return { error: "Informe uma série de 0 a 889." };
  if (current.proximoNumero > 999999999)
    return { error: "Esta série atingiu o limite de numeração. Escolha outra série." };
  if (!/^[0-9]{1,9}$/.test(form.proximo_numero) || Number(form.proximo_numero) < 1) {
    return { error: "Informe o próximo número de 1 a 999.999.999. Digite apenas os números." };
  }
  const next = Number(form.proximo_numero);
  if (next === current.proximoNumero)
    return { error: "Esse já é o próximo número. Nenhum ajuste é necessário." };
  if (next < current.proximoNumero)
    return { error: "O próximo número deve ser maior que o atual. A numeração só avança." };
  return {
    current,
    payload: {
      serie: current.serie,
      ambiente_codigo: Number(form.ambiente_codigo),
      modelo: 55,
      proximo_numero: next,
      ultimo_numero_consultado: current.ultimoNumero,
    },
  };
}

export function numberingRows(data) {
  if (!Array.isArray(data?.series)) throw new Error("Resposta de numeração inválida.");
  const keys = new Set();
  for (const row of data.series) {
    const key = `${Number(row.serie)}:${row.modelo}:${row.ambienteCodigo}`;
    if (
      typeof row.serie !== "string" ||
      !/^[0-9]{1,3}$/.test(row.serie) ||
      Number(row.serie) > 889 ||
      ![55, 65].includes(row.modelo) ||
      ![1, 2].includes(row.ambienteCodigo) ||
      !Number.isInteger(row.ultimoNumero) ||
      row.ultimoNumero < 0 ||
      row.ultimoNumero > 999999999 ||
      row.proximoNumero !== row.ultimoNumero + 1 ||
      keys.has(key)
    ) {
      throw new Error("Resposta de numeração inválida.");
    }
    keys.add(key);
  }
  return data.series;
}
