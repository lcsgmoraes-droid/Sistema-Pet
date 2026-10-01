import { arredondarDinheiro, obterPrecoVendaPDV } from "./pdvCarrinhoItensUtils.js";

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

export function calcularPesoEtiquetaBalanca(etiqueta, precoKg) {
  const precoKgCentavos = Math.round(precoKg * 100);
  if (
    !Number.isFinite(precoKg) ||
    precoKgCentavos <= 0 ||
    Math.abs(precoKg * 100 - precoKgCentavos) > 0.00001
  ) {
    return { erro: "Informe o preço por kg impresso na etiqueta." };
  }

  // Descobre todos os pesos em gramas que arredondariam para o total impresso.
  const limiteInferior = Math.ceil(
    ((2 * etiqueta.totalCentavos - 1) * 1000) / (2 * precoKgCentavos),
  );
  const limiteSuperior =
    Math.ceil(((2 * etiqueta.totalCentavos + 1) * 1000) / (2 * precoKgCentavos)) - 1;

  if (limiteInferior > limiteSuperior || limiteSuperior < 1) {
    return { erro: "Este preço por kg não fecha com o total da etiqueta." };
  }
  if (limiteInferior !== limiteSuperior) {
    return {
      erro: "O valor permite mais de um peso. Informe também o peso impresso na etiqueta.",
    };
  }

  return { quantidade: limiteInferior / 1000 };
}

export function compararPrecosEtiquetaBalanca(etiqueta, produto, precoKgEtiqueta, pesoInformado) {
  if (!produtoAceitaEtiquetaBalanca(produto)) {
    return { erro: "Marque este produto como granel e use a unidade KG." };
  }

  const resultadoPeso = calcularPesoEtiquetaBalanca(etiqueta, precoKgEtiqueta);
  const temPesoInformado =
    pesoInformado !== undefined && pesoInformado !== null && pesoInformado !== "";
  let quantidade = resultadoPeso.quantidade;

  if (temPesoInformado) {
    const peso = Number(String(pesoInformado).replace(",", "."));
    const gramas = Math.round(peso * 1000);
    if (!Number.isFinite(peso) || gramas < 1 || Math.abs(peso * 1000 - gramas) > 0.00001) {
      return { erro: "Informe o peso impresso em kg com até três casas decimais." };
    }
    const totalPesoCentavos = Math.round((gramas * Math.round(precoKgEtiqueta * 100)) / 1000);
    if (resultadoPeso.erro && !/mais de um peso/.test(resultadoPeso.erro)) {
      return resultadoPeso;
    }
    if (totalPesoCentavos !== etiqueta.totalCentavos) {
      return { erro: "Peso e preço por kg informados não fecham com o total da etiqueta." };
    }
    quantidade = gramas / 1000;
  } else if (resultadoPeso.erro) {
    return resultadoPeso;
  }

  const precoKgSistema = obterPrecoVendaPDV(produto);
  const precoSistemaValido = Number.isFinite(precoKgSistema) && precoKgSistema > 0;
  return {
    codigo: etiqueta.codigo,
    quantidade,
    precoKgEtiqueta,
    precoKgSistema: precoSistemaValido ? precoKgSistema : null,
    totalEtiqueta: etiqueta.totalCentavos / 100,
    totalSistema: precoSistemaValido ? arredondarDinheiro(quantidade * precoKgSistema) : null,
    pesoInformado: temPesoInformado,
  };
}

export function calcularItemEtiquetaBalanca(etiqueta, produto) {
  if (!produtoAceitaEtiquetaBalanca(produto)) {
    return { erro: "Marque este produto como granel e use a unidade KG." };
  }

  const precoKg = obterPrecoVendaPDV(produto);
  const resultadoPeso = calcularPesoEtiquetaBalanca(etiqueta, precoKg);
  if (resultadoPeso.erro) return resultadoPeso;

  return {
    codigo: etiqueta.codigo,
    quantidade: resultadoPeso.quantidade,
    precoUnitario: precoKg,
    subtotal: etiqueta.totalCentavos / 100,
  };
}
