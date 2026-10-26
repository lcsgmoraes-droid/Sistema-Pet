export function referenciaClonagem(nota) {
  return {
    provedor: nota.provedor === "intnfe" ? "intnfe" : "bling",
    venda_id: nota.venda_id || undefined,
    nfe_id: String(nota.id || ""),
    modelo: Number(nota.modelo) || 55,
  };
}

// CNPJ público da Amazon Serviços de Varejo do Brasil Ltda.; sempre revisável.
export const CNPJ_PUBLICO_AMAZON = "15436940000103";
export const FONTE_CNPJ_AMAZON = "https://venda.amazon.com.br/termos/stone";

export function canalComercialClone(dados = {}) {
  if (dados.intermediador) {
    return String(dados.intermediador.cnpj || "").replaceAll(/\D/g, "") === CNPJ_PUBLICO_AMAZON
      ? "amazon"
      : "intermediacao_existente";
  }
  if (String(dados.indicadorPresenca) === "1") return "loja_fisica";
  if (String(dados.indicadorPresenca) === "2") return "venda_direta_online";
  return "preservar";
}

export function atualizarCanalClone(dados, canal) {
  const copia = structuredClone(dados);
  if (canal === "amazon") {
    const mesmaAmazon =
      String(copia.intermediador?.cnpj || "").replaceAll(/\D/g, "") === CNPJ_PUBLICO_AMAZON;
    copia.indicadorPresenca = "2";
    copia.intermediador = {
      cnpj: CNPJ_PUBLICO_AMAZON,
      identificadorCadastro: mesmaAmazon ? copia.intermediador.identificadorCadastro || "" : "",
    };
  } else if (["loja_fisica", "venda_direta_online"].includes(canal)) {
    copia.indicadorPresenca = canal === "loja_fisica" ? "1" : "2";
    delete copia.intermediador;
  }
  return copia;
}

export function atualizarCampoClone(dados, caminho, valor) {
  const copia = structuredClone(dados);
  const partes = caminho.split(".");
  let destino = copia;
  for (const parte of partes.slice(0, -1)) destino = destino[parte] ??= {};
  destino[partes.at(-1)] = valor;
  if (partes[0] === "produtos" && ["quantidade", "valorUnitario"].includes(partes.at(-1))) {
    const item = copia.produtos[Number(partes[1])];
    item.valorTotal =
      Math.round((Number(item.quantidade) * Number(item.valorUnitario) + Number.EPSILON) * 100) /
      100;
  }
  return copia;
}

export function totalClonagem(dados = {}) {
  const produtos = (dados.produtos || []).reduce(
    (soma, item) =>
      soma +
      Number(item.valorTotal || 0) -
      Number(item.desconto || 0) +
      Number(item.impostos?.ipi?.valor || 0),
    0,
  );
  return Math.round((produtos + Number(dados.frete?.valor || 0) + Number.EPSILON) * 100) / 100;
}
