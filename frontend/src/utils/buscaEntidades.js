import { obterCodigoPessoaPublico, obterCodigoProdutoPublico } from "./codigosPublicos.js";

export function normalizarBusca(valor) {
  return String(valor ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR")
    .trim()
    .replace(/\s+/g, " ");
}

export function ordenarSugestoesEntidade(itens = [], termo = "", tipo = "pessoa") {
  const alvo = normalizarBusca(termo);
  if (!alvo) return itens;
  const palavras = alvo.split(" ");
  const prioridade = (item) => {
    const codigo = normalizarBusca(
      tipo === "produto" ? obterCodigoProdutoPublico(item) : obterCodigoPessoaPublico(item),
    );
    const nome = normalizarBusca(item?.nome || item?.razao_social || item?.nome_fantasia);
    const codigos =
      tipo === "produto"
        ? [codigo, item?.sku, item?.codigo_barras, item?.gtin_ean].map(normalizarBusca)
        : [codigo];
    if (codigos.some((valor) => valor && valor === alvo)) return 0;
    if (nome === alvo) return 1;
    if (codigos.some((valor) => valor && valor.startsWith(alvo))) return 2;
    if (nome.startsWith(alvo)) return 3;
    if (palavras.every((palavra) => nome.split(" ").some((parte) => parte.startsWith(palavra))))
      return 4;
    if (codigos.some((valor) => valor.includes(alvo))) return 5;
    return 6;
  };
  // Preservar o desempate do servidor (telefone, contatos e outros filtros).
  return itens
    .map((item, indice) => ({ item, indice, peso: prioridade(item) }))
    .sort((a, b) => a.peso - b.peso || a.indice - b.indice)
    .map(({ item }) => item);
}
