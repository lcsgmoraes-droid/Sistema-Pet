const UNIDADES = ["", "um", "dois", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove"];
const DEZ_A_DEZENOVE = [
  "dez",
  "onze",
  "doze",
  "treze",
  "quatorze",
  "quinze",
  "dezesseis",
  "dezessete",
  "dezoito",
  "dezenove",
];
const DEZENAS = [
  "",
  "",
  "vinte",
  "trinta",
  "quarenta",
  "cinquenta",
  "sessenta",
  "setenta",
  "oitenta",
  "noventa",
];
const CENTENAS = [
  "",
  "cento",
  "duzentos",
  "trezentos",
  "quatrocentos",
  "quinhentos",
  "seiscentos",
  "setecentos",
  "oitocentos",
  "novecentos",
];

function ateMil(numero) {
  const valor = Math.trunc(numero);
  if (valor === 0) return "zero";
  if (valor === 100) return "cem";
  const partes = [];
  const centena = Math.trunc(valor / 100);
  const resto = valor % 100;
  if (centena) partes.push(CENTENAS[centena]);
  if (resto >= 10 && resto < 20) {
    partes.push(DEZ_A_DEZENOVE[resto - 10]);
  } else {
    const dezena = Math.trunc(resto / 10);
    const unidade = resto % 10;
    if (dezena) partes.push(DEZENAS[dezena]);
    if (unidade) partes.push(UNIDADES[unidade]);
  }
  return partes.join(" e ");
}

function inteiroPorExtenso(numero) {
  if (numero < 1000) return ateMil(numero);
  if (numero < 1000000) {
    const milhares = Math.trunc(numero / 1000);
    const resto = numero % 1000;
    const prefixo = milhares === 1 ? "mil" : ateMil(milhares) + " mil";
    return resto
      ? prefixo + (resto < 100 || resto % 100 === 0 ? " e " : " ") + ateMil(resto)
      : prefixo;
  }
  return String(numero);
}

export function valorPorExtenso(valor) {
  const centavosTotais = Math.max(0, Math.round(Number(valor || 0) * 100));
  const reais = Math.trunc(centavosTotais / 100);
  const centavos = centavosTotais % 100;
  const partes = [];
  if (reais) partes.push(inteiroPorExtenso(reais) + (reais === 1 ? " real" : " reais"));
  if (centavos) partes.push(ateMil(centavos) + (centavos === 1 ? " centavo" : " centavos"));
  return partes.length ? partes.join(" e ") : "zero real";
}
