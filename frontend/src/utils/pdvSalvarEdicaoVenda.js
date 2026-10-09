import { obterTotalRecebidoExistente } from "../components/modalPagamentoUtils.js";
import { normalizarDescontosVenda, obterDescontoItem } from "./pdvDescontosUtils.js";
import { arredondarDinheiro } from "./pdvCarrinhoItensUtils.js";

function preservarMetodoDesconto(item, anteriores) {
  const anterior = anteriores.get(item.item_id_anterior ?? item.id) || anteriores.get(item.id);
  if (!anterior) return item;

  if (anterior.tipo_desconto_aplicado === "valor") {
    return { ...item, tipo_desconto_aplicado: "valor" };
  }
  const percentual = Number(anterior.desconto_percentual);
  const bruto = arredondarDinheiro(Number(item.preco_unitario || 0) * Number(item.quantidade || 0));
  const esperado = arredondarDinheiro((bruto * percentual) / 100);
  if (
    anterior.tipo_desconto_aplicado === "percentual" &&
    anterior.desconto_percentual != null &&
    anterior.desconto_percentual !== "" &&
    Number.isFinite(percentual) &&
    percentual >= 0 &&
    percentual <= 100 &&
    esperado === obterDescontoItem(item)
  ) {
    return { ...item, tipo_desconto_aplicado: "percentual", desconto_percentual: percentual };
  }
  return item;
}

export function montarVendaPersistidaParaEdicao(
  anterior,
  persistida,
  recebido = anterior.total_pago,
) {
  const anteriores = new Map(
    (anterior.itens || [])
      .filter((item) => item.venda_id != null && Number(item.venda_id) === Number(anterior.id))
      .map((item) => [item.id, item]),
  );
  const itens =
    persistida.itens?.map((item) => preservarMetodoDesconto(item, anteriores)) ?? anterior.itens;
  return normalizarDescontosVenda({
    ...anterior,
    ...persistida,
    // Cada linha do servidor tem a identidade atual; produto repetido nao
    // identifica uma linha. Nao associa IDs antigos por produto ou posicao.
    itens,
    cliente: anterior.cliente,
    pet: anterior.pet,
    entrega: { ...anterior.entrega, ...persistida.entrega },
    cupons_detalhes: persistida.cupons_detalhes ?? anterior.cupons_detalhes,
    pagamentos: anterior.pagamentos,
    total_pago: recebido,
  });
}

export async function salvarEdicaoVenda({
  vendaAtual,
  payloadVenda,
  atualizarVenda,
  buscarPagamentos,
  finalizarVenda,
  onVendaPersistida,
}) {
  const atualizada = await atualizarVenda(vendaAtual.id, payloadVenda);
  await onVendaPersistida?.(atualizada);
  const resumo = await buscarPagamentos(vendaAtual.id);
  const recebido = obterTotalRecebidoExistente(resumo);
  const total = Number(atualizada.total ?? vendaAtual.total);

  if (recebido > 0 && recebido >= total - 0.01) {
    // Uma venda reaberta devolveu estoque e beneficios. Fechar pelo mesmo
    // orquestrador do pagamento reaplica esses efeitos sem cobrar de novo.
    const resultado = await finalizarVenda(vendaAtual.id, [], {
      cupom_code: payloadVenda.cupom_code,
      cupom_discount_applied: payloadVenda.cupom_discount_applied,
      nao_gerar_beneficios: Boolean(atualizada.nao_gerar_beneficios),
      justificativa_nao_gerar_beneficios: atualizada.justificativa_nao_gerar_beneficios || null,
    });
    return { venda: resultado.venda || atualizada, recebido, finalizada: true };
  }

  return { venda: atualizada, recebido, finalizada: false };
}
