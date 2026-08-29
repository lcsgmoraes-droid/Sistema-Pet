export const FORMATOS_OFERTA = {
  quadrado: { label: "Instagram quadrado", ratio: "1 / 1", width: 1080, height: 1080 },
  retrato: { label: "Feed vertical", ratio: "4 / 5", width: 1080, height: 1350 },
  story: { label: "Story / Status", ratio: "9 / 16", width: 1080, height: 1920 },
  a4: { label: "A4 para impressão", ratio: "210 / 297", width: 1240, height: 1754 },
};

export const TIPOS_ARTE = {
  jornal: { label: "Jornal / panfleto", descricao: "Vários produtos por página" },
  individual: { label: "Um produto por página", descricao: "Card completo com oferta" },
  produto: { label: "Só a imagem do produto", descricao: "Sem preço ou textos na imagem" },
};

export const PERIODICIDADES = {
  diaria: "Jornal diário",
  semanal: "Jornal semanal",
  mensal: "Jornal mensal",
  avulsa: "Promoção avulsa",
};

export const ESTRATEGIAS = {
  mesclado: "Seleção inteligente mesclada",
  mais_vendidos: "Mais vendidos",
  melhor_margem: "Melhores margens",
  baixo_giro: "Baixo giro",
  estoque_alto: "Estoque elevado",
  validade_proxima: "Validade próxima",
};

function localDateTimeValue(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

export function criarPeriodo(periodicidade, base = new Date()) {
  const inicio = new Date(base);
  inicio.setSeconds(0, 0);
  const fim = new Date(inicio);
  if (periodicidade === "diaria") {
    fim.setHours(23, 59, 0, 0);
    if (fim <= inicio) fim.setDate(fim.getDate() + 1);
  } else if (periodicidade === "semanal") fim.setDate(fim.getDate() + 7);
  else if (periodicidade === "mensal") fim.setMonth(fim.getMonth() + 1);
  else fim.setDate(fim.getDate() + 3);
  return {
    inicio: localDateTimeValue(inicio),
    fim: localDateTimeValue(fim),
    expira: localDateTimeValue(fim),
  };
}

export function criarItemSelecionado(produto, usarValidade = false) {
  const validadeAtiva = Boolean(usarValidade && produto.lote_validade);
  return {
    ...produto,
    produto_id: produto.id,
    preco_arte:
      validadeAtiva && produto.preco_sugerido_validade
        ? produto.preco_sugerido_validade
        : produto.preco_erp,
    mostrar_validade: validadeAtiva,
    lote_id: validadeAtiva ? produto.lote_validade.id : null,
    imagem_original_url: produto.imagem_url || null,
    imagem_gerada_url: null,
    imagem_url_arte: produto.imagem_url || null,
  };
}

export function calcularDesconto(precoBase, precoArte) {
  const base = Number(precoBase || 0);
  const arte = Number(precoArte || 0);
  if (base <= 0 || arte >= base) return 0;
  return Math.round(((base - arte) / base) * 10000) / 100;
}

export function calcularMargem(precoArte, precoCusto) {
  const preco = Number(precoArte || 0);
  const custo = Number(precoCusto || 0);
  if (preco <= 0) return 0;
  return Math.round(((preco - custo) / preco) * 10000) / 100;
}

export function itensPorPagina(tipoArte, formato) {
  if (tipoArte !== "jornal") return 1;
  if (formato === "quadrado") return 6;
  if (formato === "story") return 5;
  return 8;
}

export function agruparPaginas(itens, tipoArte, formato) {
  const tamanho = itensPorPagina(tipoArte, formato);
  const paginas = [];
  for (let index = 0; index < itens.length; index += tamanho) {
    paginas.push(itens.slice(index, index + tamanho));
  }
  return paginas;
}

export function montarPayloadPublicacao({
  titulo,
  periodicidade,
  tipoArte,
  formato,
  inicio,
  fim,
  expira,
  itens,
  tema,
}) {
  return {
    titulo: titulo.trim(),
    periodicidade,
    tipo_arte: tipoArte,
    formato,
    inicio_em: new Date(inicio).toISOString(),
    fim_em: new Date(fim).toISOString(),
    expira_em: new Date(expira).toISOString(),
    produtos: itens.map((item) => ({
      produto_id: item.produto_id,
      preco_arte: Number(item.preco_arte),
      imagem_url: item.imagem_url_arte || item.imagem_url || null,
      mostrar_validade: Boolean(item.mostrar_validade),
      lote_id: item.mostrar_validade ? item.lote_id : null,
    })),
    configuracao: { tema },
  };
}
