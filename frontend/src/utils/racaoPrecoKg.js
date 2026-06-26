import { formatMoneyBRL } from "./formatters.js";

const arredondarMoeda = (valor) => Math.round((valor + Number.EPSILON) * 100) / 100;

const normalizarNumero = (valor) => {
  if (typeof valor === "number") {
    return Number.isFinite(valor) ? valor : null;
  }

  if (valor === null || valor === undefined) {
    return null;
  }

  const texto = String(valor).trim();
  if (!texto) {
    return null;
  }

  const normalizado = texto.includes(",") ? texto.replace(/\./g, "").replace(",", ".") : texto;
  const numero = Number.parseFloat(normalizado);

  return Number.isFinite(numero) ? numero : null;
};

export function obterPesoEmbalagemKg(produto) {
  const peso = normalizarNumero(
    produto?.peso_embalagem ??
      produto?.peso_embalagem_kg ??
      produto?.peso_pacote_kg ??
      produto?.peso_liquido ??
      produto?.peso_bruto,
  );

  return peso && peso > 0 ? peso : null;
}

export function obterPrecoVendaParaKg(produto) {
  const preco = normalizarNumero(
    produto?.preco_venda_pdv ??
      produto?.preco_venda_efetivo ??
      produto?.preco_venda ??
      produto?.preco_unitario ??
      produto?.preco,
  );

  return preco && preco > 0 ? preco : null;
}

export function calcularPrecoPorKg(produto) {
  const pesoKg = obterPesoEmbalagemKg(produto);
  const preco = obterPrecoVendaParaKg(produto);

  if (!pesoKg || !preco) {
    return null;
  }

  return arredondarMoeda(preco / pesoKg);
}

export function formatarPesoKg(valor) {
  const pesoKg = typeof valor === "object" ? obterPesoEmbalagemKg(valor) : normalizarNumero(valor);

  if (!pesoKg || pesoKg <= 0) {
    return "";
  }

  return `${pesoKg.toLocaleString("pt-BR", { maximumFractionDigits: 3 })}kg`;
}

export function formatarPrecoPorKg(produto) {
  const precoPorKg = calcularPrecoPorKg(produto);

  return precoPorKg ? `${formatMoneyBRL(precoPorKg)}/kg` : "";
}

export function obterResumoPrecoPorKg(produto) {
  const pesoKg = obterPesoEmbalagemKg(produto);
  const preco = obterPrecoVendaParaKg(produto);
  const precoPorKg = calcularPrecoPorKg(produto);
  const produtoId = produto?.produto_id ?? produto?.id ?? produto?.produto?.id;
  const nome = produto?.produto_nome ?? produto?.nome ?? produto?.produto?.nome ?? "Produto";

  if (!pesoKg || !preco || !precoPorKg) {
    return {
      disponivel: false,
      nome,
      pesoKg,
      preco,
      precoPorKg,
      pesoFormatado: pesoKg ? formatarPesoKg(pesoKg) : "",
      precoFormatado: preco ? formatMoneyBRL(preco) : "",
      precoPorKgFormatado: "",
    };
  }

  const resumo = {
    disponivel: true,
    nome,
    pesoKg,
    preco,
    precoPorKg,
    pesoFormatado: formatarPesoKg(pesoKg),
    precoFormatado: formatMoneyBRL(preco),
    precoPorKgFormatado: `${formatMoneyBRL(precoPorKg)}/kg`,
  };

  if (produtoId !== null && produtoId !== undefined) {
    resumo.produtoId = produtoId;
  }

  return resumo;
}

export function compararRacoesPorPrecoKg(produtos = []) {
  const ordenados = produtos
    .map((produto, index) => ({
      ...obterResumoPrecoPorKg(produto),
      ordemOriginal: index,
    }))
    .filter((item) => item.disponivel)
    .sort((a, b) => {
      if (a.precoPorKg !== b.precoPorKg) {
        return a.precoPorKg - b.precoPorKg;
      }

      return a.nome.localeCompare(b.nome, "pt-BR");
    });

  const melhorPreco = ordenados[0]?.precoPorKg ?? null;

  return ordenados.map((item) => {
    const diferencaMelhor =
      melhorPreco === null ? 0 : arredondarMoeda(item.precoPorKg - melhorPreco);

    return {
      ...item,
      melhorOpcao: diferencaMelhor === 0,
      diferencaMelhor,
      diferencaMelhorFormatada:
        diferencaMelhor > 0 ? `+${formatMoneyBRL(diferencaMelhor)}/kg` : "Melhor preco/kg",
    };
  });
}
