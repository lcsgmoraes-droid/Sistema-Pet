function numeroSeguro(valor) {
  const numero = Number(valor || 0);
  return Number.isFinite(numero) ? numero : 0;
}

export const CANAIS_DESTAQUE = ["loja_fisica", "mercado_livre", "shopee", "amazon"];

export const LABELS_CANAIS = {
  loja_fisica: "Loja FÃ­sica",
  mercado_livre: "Mercado Livre",
  shopee: "Shopee",
  amazon: "Amazon",
  site: "Site",
  instagram: "Instagram",
  whatsapp: "WhatsApp",
};

export const ESTILOS_CANAIS = {
  loja_fisica: {
    card: "bg-emerald-50 border-emerald-200 text-emerald-700",
    bar: "bg-emerald-400",
  },
  mercado_livre: {
    card: "bg-yellow-50 border-yellow-200 text-yellow-700",
    bar: "bg-yellow-400",
  },
  shopee: {
    card: "bg-orange-50 border-orange-200 text-orange-700",
    bar: "bg-orange-400",
  },
  amazon: {
    card: "bg-sky-50 border-sky-200 text-sky-700",
    bar: "bg-sky-400",
  },
  site: {
    card: "bg-indigo-50 border-indigo-200 text-indigo-700",
    bar: "bg-indigo-400",
  },
  instagram: {
    card: "bg-pink-50 border-pink-200 text-pink-700",
    bar: "bg-pink-400",
  },
  whatsapp: {
    card: "bg-green-50 border-green-200 text-green-700",
    bar: "bg-green-400",
  },
};

export function formatarQuantidadeMovimentacao(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function parseNumeroInputMovimentacao(valor) {
  if (valor === null || valor === undefined || valor === "") return 0;
  if (typeof valor === "number") return Number.isFinite(valor) ? valor : 0;

  const texto = String(valor).trim();
  const normalizado = texto.includes(",") ? texto.replace(/\./g, "").replace(",", ".") : texto;
  const numero = Number(normalizado);
  return Number.isFinite(numero) ? numero : 0;
}

export function dataAtualIsoLocalMovimentacao() {
  const agora = new Date();
  const local = new Date(agora.getTime() - agora.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

export function extrairMensagemErroApiMovimentacao(error, fallback) {
  const detalhe = error?.response?.data?.detail ?? error?.response?.data?.message;
  if (typeof detalhe === "string") return detalhe;
  if (detalhe && typeof detalhe === "object") {
    return detalhe.message || detalhe.mensagem || fallback;
  }
  return error?.message || fallback;
}

export function getSaldoAposLancamento(movimentacao) {
  const saldo = movimentacao?.saldo_apos_lancamento ?? movimentacao?.quantidade_nova;
  const saldoNumerico = Number(saldo);
  return Number.isFinite(saldoNumerico) ? saldoNumerico : null;
}

export function getMotivoLabelMovimentacao(motivo) {
  const labels = {
    compra: "Compra",
    venda: "Venda",
    venda_online: "Venda Online",
    ajuste: "Ajuste",
    saida_manual: "Saida Manual",
    devolucao: "Devolucao",
    perda: "Perda",
    avaria: "Avaria",
    roubo: "Roubo/Furto",
    amostra: "Amostra",
    uso_interno: "Uso interno",
    devolucao_fornecedor: "Devolucao ao fornecedor",
    transferencia: "Transferencia",
    balanco: "Balanco",
  };
  return labels[motivo] || motivo;
}

export function getOrigemMovimentacao(mov) {
  if (mov.referencia_tipo === "venda_excluida") {
    return {
      texto: `Venda Cancelada #${mov.referencia_id}`,
      icone: "cancelado",
      cor: "text-gray-400",
      link: null,
    };
  }

  if (mov.referencia_tipo === "venda") {
    if (mov.documento && (mov.documento.length === 44 || mov.documento.startsWith("NF"))) {
      return { texto: `NF ${mov.documento}`, icone: "nf-venda", cor: "text-red-600", link: null };
    }
    return {
      texto: `Pedido #${mov.referencia_id}`,
      icone: "pedido",
      cor: "text-orange-600",
      link: `/pdv?venda=${mov.referencia_id}`,
    };
  }

  if (mov.referencia_tipo === "pedido_integrado") {
    if (mov.nf_numero) {
      return { texto: `NF ${mov.nf_numero}`, icone: "nf-venda", cor: "text-red-600", link: null };
    }
    if (mov.documento) {
      return {
        texto: `Pedido Bling #${mov.documento}`,
        icone: "pedido",
        cor: "text-orange-600",
        link: null,
      };
    }
    return {
      texto: `Pedido Bling #${mov.referencia_id}`,
      icone: "pedido",
      cor: "text-orange-600",
      link: null,
    };
  }

  if (mov.motivo === "balanco") {
    return { texto: "Balanco", icone: "balanco", cor: "text-blue-600", link: null };
  }

  if (mov.tipo === "saida") {
    return {
      texto: getMotivoLabelMovimentacao(mov.motivo),
      icone: "manual",
      cor: "text-red-600",
      link: null,
    };
  }

  if (mov.tipo === "entrada" && mov.documento && mov.documento.length === 44) {
    return {
      texto: `NF ${mov.documento.substring(25, 34)}`,
      icone: "nf-entrada",
      cor: "text-green-600",
      link: null,
    };
  }

  if (mov.tipo === "entrada" && mov.documento) {
    return {
      texto: mov.documento,
      icone: "documento",
      cor: "text-blue-600",
      link: `/pdv?venda=${mov.documento}`,
    };
  }

  if (mov.tipo === "entrada") {
    return { texto: "Entrada Manual", icone: "manual", cor: "text-green-600", link: null };
  }

  return { texto: "Manual", icone: "manual", cor: "text-gray-500", link: null };
}

export function calcularTotaisMovimentacoes(movimentacoes = []) {
  return {
    totalEntradas: movimentacoes
      .filter((m) => m.tipo === "entrada" && m.status !== "cancelado")
      .reduce((sum, m) => sum + parseFloat(m.quantidade || 0), 0),
    totalSaidas: movimentacoes
      .filter((m) => m.tipo === "saida" && m.status !== "cancelado")
      .reduce((sum, m) => sum + parseFloat(m.quantidade || 0), 0),
  };
}

export function calcularVendasPorCanalMovimentacoes(movimentacoes = []) {
  const isSaidaVendaVinculada = (mov) => {
    if (mov?.tipo !== "saida" || mov?.status === "cancelado" || !mov?.canal) {
      return false;
    }

    if (mov.referencia_tipo === "venda") {
      return true;
    }

    if (mov.referencia_tipo === "pedido_integrado") {
      return Boolean(
        mov.nf_numero || (typeof mov.documento === "string" && mov.documento.startsWith("NF ")),
      );
    }

    return false;
  };

  const grupos = {};
  movimentacoes.filter(isSaidaVendaVinculada).forEach((m) => {
    const canal = m.canal;
    if (!grupos[canal]) grupos[canal] = { qtd: 0, valor: 0, count: 0 };
    grupos[canal].qtd += parseFloat(m.quantidade || 0);
    grupos[canal].valor += m.preco_venda_unitario
      ? parseFloat(m.quantidade || 0) * parseFloat(m.preco_venda_unitario)
      : 0;
    grupos[canal].count += 1;
  });

  const temVendasPorCanal = Object.values(grupos).some((g) => g.count > 0);
  if (!temVendasPorCanal) {
    return [];
  }

  CANAIS_DESTAQUE.forEach((canal) => {
    if (!grupos[canal]) {
      grupos[canal] = { qtd: 0, valor: 0, count: 0 };
    }
  });

  const totalQtd = Object.values(grupos).reduce((s, g) => s + g.qtd, 0);
  return Object.entries(grupos)
    .filter(([canal, g]) => g.count > 0 || CANAIS_DESTAQUE.includes(canal))
    .map(([canal, g]) => ({
      canal,
      qtd: g.qtd,
      valor: g.valor,
      count: g.count,
      pct: totalQtd > 0 ? (g.qtd / totalQtd) * 100 : 0,
    }))
    .sort((a, b) => {
      if (b.qtd !== a.qtd) return b.qtd - a.qtd;

      const aIndex = CANAIS_DESTAQUE.indexOf(a.canal);
      const bIndex = CANAIS_DESTAQUE.indexOf(b.canal);
      if (aIndex !== -1 || bIndex !== -1) {
        return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
      }

      return a.canal.localeCompare(b.canal);
    });
}

export function produtoUsaEstoqueVirtual(produto) {
  return (
    (produto?.tipo_produto === "KIT" || produto?.tipo_produto === "VARIACAO") &&
    produto?.tipo_kit === "VIRTUAL"
  );
}

export function resolverEstoqueAtualMovimentacoes(produto) {
  if (produtoUsaEstoqueVirtual(produto)) {
    return numeroSeguro(produto?.estoque_virtual ?? produto?.estoque_disponivel);
  }

  return numeroSeguro(produto?.estoque_atual);
}

export function resolverSaldoDisponivelMovimentacoes(produto) {
  if (produtoUsaEstoqueVirtual(produto)) {
    return numeroSeguro(produto?.estoque_disponivel ?? produto?.estoque_virtual);
  }

  const estoqueAtual = resolverEstoqueAtualMovimentacoes(produto);
  const estoqueReservado = numeroSeguro(produto?.estoque_reservado);
  return estoqueAtual - estoqueReservado;
}
