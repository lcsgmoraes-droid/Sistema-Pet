import { arredondarDinheiro } from "./pdvCarrinhoItensUtils.js";

const dinheiro = (valor) => Math.max(0, arredondarDinheiro(valor));

export function obterDescontoItem(item = {}) {
  return dinheiro(item.desconto_valor ?? item.desconto_item ?? 0);
}

export function normalizarDescontosVenda(venda = {}) {
  const itens = (venda.itens || []).map((item) => ({
    ...item,
    desconto_valor: obterDescontoItem(item),
  }));
  if (venda.desconto_venda_valor == null) {
    // A origem do desconto antigo nao e comprovada. Preserva cada linha e
    // o contrato financeiro legado, inclusive em uma simples refinalizacao.
    return { ...venda, itens, desconto_venda_valor: null, desconto_origem_legado: true };
  }
  const normalizada = { ...venda, itens };
  return {
    ...normalizada,
    cupons_detalhes: calcularCuponsVenda(
      Math.max(0, Number(venda.subtotal || 0) - Number(venda.desconto_venda_valor || 0)),
      obterCuponsVenda(normalizada),
    ).detalhes,
  };
}

export function obterCuponsVenda(venda = {}) {
  const codigos = String(venda.cupom_code || "")
    .split(",")
    .map((codigo) => codigo.trim().toUpperCase())
    .filter(Boolean);
  return codigos.map((code, index) => {
    const detalhe = venda.cupons_detalhes?.find((cupom) => cupom.code === code);
    return (
      detalhe || {
        code,
        discount_applied: index === 0 ? dinheiro(venda.cupom_discount_applied) : 0,
        persistido_sem_detalhe: true,
      }
    );
  });
}

export function converterDescontosLegados(venda) {
  if (venda.desconto_venda_valor != null) return venda;
  const normalizada = normalizarDescontosVenda(venda);
  const bruto = dinheiro(
    normalizada.itens.reduce(
      (sum, item) =>
        sum + dinheiro(Number(item.preco_unitario || 0) * Number(item.quantidade || 0)),
      0,
    ),
  );
  const frete = venda.tem_entrega
    ? Number(venda.entrega?.taxa_entrega_total ?? venda.taxa_entrega ?? 0)
    : 0;
  const historico = dinheiro(bruto + frete - Number(venda.total || 0));
  const cupom = venda.cupom_code ? Math.min(dinheiro(venda.cupom_discount_applied), historico) : 0;
  const anteriores = normalizada.itens.reduce((sum, item) => sum + item.desconto_valor, 0);
  const manual = Math.min(anteriores, dinheiro(historico - cupom));
  const ultimo = normalizada.itens.filter((item) => item.desconto_valor > 0).at(-1);
  let alocado = 0;
  const itens = normalizada.itens.map((item) => {
    const proporcional =
      item === ultimo
        ? dinheiro(manual - alocado)
        : anteriores > 0
          ? dinheiro((manual * item.desconto_valor) / anteriores)
          : 0;
    const desconto = Math.min(proporcional, dinheiro(manual - alocado));
    alocado = dinheiro(alocado + desconto);
    return {
      ...item,
      desconto_valor: desconto,
      desconto_item: desconto,
      subtotal: dinheiro(
        dinheiro(Number(item.preco_unitario || 0) * Number(item.quantidade || 0)) - desconto,
      ),
    };
  });
  return {
    ...normalizada,
    itens,
    subtotal: dinheiro(itens.reduce((sum, item) => sum + item.subtotal, 0)),
    desconto_venda_valor: dinheiro(historico - manual - cupom),
    desconto_valor: historico,
    cupom_discount_applied: venda.cupom_code ? cupom : null,
    desconto_origem_legado: false,
  };
}

export function calcularCuponsVenda(base, cupons = []) {
  let restante = dinheiro(base);
  const detalhes = cupons.map((cupom) => {
    const valor =
      cupom.coupon_type === "percent"
        ? dinheiro((restante * Math.min(100, dinheiro(cupom.discount_percent))) / 100)
        : cupom.coupon_type === "fixed"
          ? dinheiro(cupom.discount_value)
          : dinheiro(cupom.discount_applied);
    const aplicado = Math.min(valor, restante);
    restante = dinheiro(restante - aplicado);
    return { ...cupom, discount_applied: aplicado };
  });
  return {
    detalhes,
    desconto: dinheiro(detalhes.reduce((sum, cupom) => sum + cupom.discount_applied, 0)),
    restante,
  };
}

export function recalcularVendaComDescontos(venda, itens = venda.itens, extras = {}) {
  const dados = { ...venda, ...extras };
  const subtotal = dinheiro(itens.reduce((sum, item) => sum + Number(item.subtotal || 0), 0));
  const descontoItens = dinheiro(itens.reduce((sum, item) => sum + obterDescontoItem(item), 0));
  const frete = dados.tem_entrega
    ? Number(dados.entrega?.taxa_entrega_total ?? dados.taxa_entrega ?? 0)
    : 0;
  if (dados.desconto_venda_valor == null) {
    const desconto =
      descontoItens > 0
        ? descontoItens
        : Number(dados.desconto_percentual) > 0
          ? dinheiro((subtotal * Number(dados.desconto_percentual)) / 100)
          : dinheiro(dados.desconto_valor);
    return {
      ...dados,
      itens,
      subtotal,
      desconto_venda_valor: null,
      desconto_valor: desconto,
      total: dinheiro(subtotal - (descontoItens > 0 ? 0 : desconto) + frete),
    };
  }
  const descontoVenda = Math.min(dinheiro(dados.desconto_venda_valor), subtotal);
  const cupons = calcularCuponsVenda(subtotal - descontoVenda, obterCuponsVenda(dados));
  const descontoCupom = cupons.desconto;
  const desconto = dinheiro(descontoItens + descontoVenda + descontoCupom);
  const bruto = subtotal + descontoItens;
  return {
    ...dados,
    itens,
    subtotal,
    desconto_venda_valor: descontoVenda,
    desconto_valor: desconto,
    desconto_percentual: bruto > 0 ? (desconto / bruto) * 100 : 0,
    cupom_discount_applied: dados.cupom_code ? descontoCupom : null,
    cupons_detalhes: cupons.detalhes,
    total: dinheiro(subtotal - descontoVenda - descontoCupom + frete),
  };
}

export function resumirDescontosVenda(venda = {}) {
  const normalizada = normalizarDescontosVenda(venda);
  const itens = dinheiro(normalizada.itens.reduce((sum, item) => sum + obterDescontoItem(item), 0));
  const global = dinheiro(normalizada.desconto_venda_valor);
  const cupom = dinheiro(normalizada.cupom_discount_applied);
  if (normalizada.desconto_venda_valor == null) {
    const total = dinheiro(normalizada.desconto_valor);
    return {
      itens,
      global: Math.max(0, dinheiro(total - itens)),
      cupom,
      manual: Math.max(0, dinheiro(total - cupom)),
      total,
    };
  }
  return {
    itens,
    global,
    cupom,
    manual: dinheiro(itens + global),
    total: dinheiro(itens + global + cupom),
  };
}
