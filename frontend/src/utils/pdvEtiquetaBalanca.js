import { obterPrecoVendaPDV } from "./pdvCarrinhoItensUtils.js";

function digitoVerificadorEan13(codigoSemDigito) {
  const soma = [...codigoSemDigito].reduce(
    (total, digito, indice) => total + Number(digito) * (indice % 2 === 0 ? 1 : 3),
    0,
  );
  return (10 - (soma % 10)) % 10;
}

// Formato configurado nas etiquetas da balanca: 2 + produto (6) + preco em centavos (5) + DV.
export function lerEtiquetaBalanca(codigoLido) {
  const codigo = String(codigoLido ?? "").trim();
  if (!/^2\d{12}$/.test(codigo)) return null;

  if (digitoVerificadorEan13(codigo.slice(0, 12)) !== Number(codigo[12])) {
    return { codigo, erro: "O código de barras da etiqueta é inválido. Leia novamente." };
  }

  const codigoProduto = codigo.slice(1, 7);
  const totalCentavos = Number(codigo.slice(7, 12));
  if (totalCentavos <= 0) {
    return { codigo, erro: "A etiqueta da balança não contém um valor de venda válido." };
  }

  return {
    codigo,
    codigoProduto,
    codigoProdutoSemZeros: codigoProduto.replace(/^0+/, "") || "0",
    totalCentavos,
  };
}

export function produtoAceitaEtiquetaBalanca(produto) {
  return produto?.e_granel === true && String(produto?.unidade || "").toUpperCase() === "KG";
}

export function calcularItemEtiquetaBalanca(etiqueta, produto) {
  const precoKg = obterPrecoVendaPDV(produto);
  const precoKgCentavos = Math.round(precoKg * 100);
  if (
    !produtoAceitaEtiquetaBalanca(produto) ||
    !Number.isFinite(precoKg) ||
    precoKgCentavos <= 0 ||
    Math.abs(precoKg * 100 - precoKgCentavos) > 0.00001
  ) {
    return {
      erro: "Marque este produto como granel, use a unidade KG e informe o preço por kg no PDV.",
    };
  }

  // Descobre todos os pesos em gramas que arredondariam para o total impresso.
  const limiteInferior = Math.ceil(
    ((2 * etiqueta.totalCentavos - 1) * 1000) / (2 * precoKgCentavos),
  );
  const limiteSuperior =
    Math.ceil(((2 * etiqueta.totalCentavos + 1) * 1000) / (2 * precoKgCentavos)) - 1;

  if (limiteInferior !== limiteSuperior || limiteInferior < 1) {
    return {
      erro: "Não foi possível determinar um peso único pelo valor da etiqueta e preço por kg. Confira o preço da balança.",
    };
  }

  return {
    codigo: etiqueta.codigo,
    quantidade: limiteInferior / 1000,
    precoUnitario: precoKg,
    subtotal: etiqueta.totalCentavos / 100,
  };
}
