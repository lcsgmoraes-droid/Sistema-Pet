import { parseNumeroInputMovimentacao } from "./movimentacoesProdutoUtils.js";

export function calcularQuantidadeDestinoFracionamento(quantidadeOrigem, fatorConversao) {
  const quantidade = parseNumeroInputMovimentacao(quantidadeOrigem);
  const fator = parseNumeroInputMovimentacao(fatorConversao);
  return quantidade > 0 && fator > 0 ? quantidade * fator : 0;
}

export function montarPayloadFracionamentoClinico({
  produtoOrigemId,
  produtoDestinoId,
  quantidadeOrigem,
  fatorConversao,
  validadeAposAberturaDias,
  loteOrigemId,
  documento,
  observacao,
}) {
  const validade = parseNumeroInputMovimentacao(validadeAposAberturaDias);
  return {
    produto_origem_id: Number(produtoOrigemId),
    produto_destino_id: Number(produtoDestinoId),
    quantidade_origem: parseNumeroInputMovimentacao(quantidadeOrigem),
    fator_conversao: parseNumeroInputMovimentacao(fatorConversao),
    validade_apos_abertura_dias: validade > 0 ? Math.trunc(validade) : null,
    lote_origem_id: loteOrigemId ? Number(loteOrigemId) : null,
    documento: documento?.trim() || null,
    observacao: observacao?.trim() || null,
  };
}

export function resolverConfiguracaoVinculoFracionamento(vinculos, produtoDestinoId) {
  return (vinculos || []).find(
    (item) => String(item.produto_destino_id) === String(produtoDestinoId),
  );
}
