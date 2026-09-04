const CONTAGEM_PREFIX = "[Contagem de cedulas]";

const DENOMINACOES = [
  ["n200", 200],
  ["n100", 100],
  ["n50", 50],
  ["n20", 20],
  ["n10", 10],
  ["n5", 5],
  ["n2", 2],
];

function moeda(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export function transcreverContagemCedulas(notas = {}) {
  const partes = DENOMINACOES.flatMap(([campo, valor]) => {
    const quantidade = Number.parseInt(notas[campo], 10) || 0;
    return quantidade > 0 ? [`${quantidade} x ${moeda(valor)} = ${moeda(quantidade * valor)}`] : [];
  });
  const moedas = Number.parseFloat(notas.moedas) || 0;
  if (moedas > 0) partes.push(`moedas = ${moeda(moedas)}`);

  const total =
    DENOMINACOES.reduce(
      (soma, [campo, valor]) => soma + (Number.parseInt(notas[campo], 10) || 0) * valor,
      0,
    ) + moedas;
  return `${CONTAGEM_PREFIX} ${partes.length ? partes.join("; ") : "sem cedulas ou moedas"}; total = ${moeda(total)}.`;
}

export function atualizarObservacaoComContagem(observacao = "", notas = {}) {
  const linhasManuais = String(observacao || "")
    .split("\n")
    .filter((linha) => !linha.trim().startsWith(CONTAGEM_PREFIX));
  const manual = linhasManuais.join("\n").trim();
  return [manual, transcreverContagemCedulas(notas)].filter(Boolean).join("\n");
}
