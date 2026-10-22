// Regras de apresentação do quadro do CRM (sem React, para testar em Node).

export const TIPOS_FINAIS = ["concluido", "encerrado"];
export const DIAS_PARA_ATENCAO = 5;
export const MAXIMO_DE_COLUNAS = 8;

export const ROTULO_TIPO_DE_COLUNA = {
  entrada: "Entrada",
  andamento: "Em andamento",
  concluido: "Concluído",
  encerrado: "Encerrado sem resultado",
};

export const ROTULO_DE_OPORTUNIDADE = {
  vacina: "Vacina",
  racao: "Ração",
  sem_comprar: "Sem comprar",
  aniversario: "Aniversário",
  cashback: "Cashback",
  vip_em_risco: "VIP em risco",
};

export function rotuloDaOportunidade(oportunidade) {
  const base = ROTULO_DE_OPORTUNIDADE[oportunidade.tipo] || oportunidade.tipo;
  return oportunidade.detalhe ? `${base}: ${oportunidade.detalhe}` : base;
}

export function colunaEhFinal(coluna) {
  return TIPOS_FINAIS.includes(coluna?.tipo);
}

function chaveDaColuna(nome) {
  return String(nome || "")
    .trim()
    .toLocaleLowerCase("pt-BR");
}

/**
 * Junta o quadro de uma ou mais lojas. Com uma loja, as colunas são as dela.
 * Com várias, colunas de mesmo nome (sem diferenciar maiúsculas) viram uma só e
 * cada card guarda a sua loja; `idPorLoja` diz qual coluna real recebe o card.
 */
export function unificarQuadros(lojas) {
  const porChave = new Map();
  for (const loja of lojas || []) {
    if (!loja.colunas) continue;
    for (const coluna of loja.colunas) {
      const chave = chaveDaColuna(coluna.nome);
      if (!porChave.has(chave)) {
        porChave.set(chave, {
          chave,
          nome: coluna.nome,
          tipo: coluna.tipo,
          ordem: coluna.ordem,
          janela_dias: coluna.janela_dias,
          total: 0,
          valor_total: 0,
          cards: [],
          idPorLoja: {},
        });
      }
      const destino = porChave.get(chave);
      destino.total += coluna.total;
      destino.valor_total += coluna.valor_total;
      destino.idPorLoja[loja.loja_id] = coluna.id;
      for (const card of coluna.cards) {
        destino.cards.push({
          ...card,
          loja_id: loja.loja_id,
          loja_nome: loja.loja_nome,
        });
      }
    }
  }
  return [...porChave.values()].sort((a, b) => a.ordem - b.ordem);
}

/** Quadro vem como [{loja_id, loja_nome, colunas}] (um item por loja). */
export function quadrosPorLoja(resposta) {
  return (resposta?.lojas || []).map((item) => ({
    loja_id: item.loja_id,
    loja_nome: item.loja_nome,
    colunas: item.colunas,
    funil_id: item.funil_id,
  }));
}

export function formatarValor(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function inicioDoDia(data) {
  const copia = new Date(data);
  copia.setHours(0, 0, 0, 0);
  return copia;
}

/**
 * Situação do próximo passo do card:
 * - "sem_passo" e "hoje" pedem atenção (amarelo), "atrasado" é vermelho, "futuro" é neutro.
 * Sempre acompanha um texto, nunca só a cor.
 */
export function situacaoDoPasso(passo, agora = new Date()) {
  if (!passo?.agendado_para) return { codigo: "sem_passo", texto: "Sem próximo passo" };
  const dia = inicioDoDia(passo.agendado_para).getTime();
  const hoje = inicioDoDia(agora).getTime();
  const data = new Date(passo.agendado_para).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
  if (dia < hoje) return { codigo: "atrasado", texto: `Atrasado desde ${data}` };
  if (dia === hoje) return { codigo: "hoje", texto: "Para hoje" };
  return { codigo: "futuro", texto: `Para ${data}` };
}

export function precisaDeAtencaoPorTempo(card) {
  return (card?.dias_na_coluna ?? 0) >= DIAS_PARA_ATENCAO;
}

/**
 * O que a movimentação exige antes de chamar a API:
 * { exigeModal, exigeMotivoDaPerda, oportunidades }.
 */
export function exigenciasDaMovimentacao(card, colunaDestino, colunaOrigem) {
  const origemFinal = colunaEhFinal(colunaOrigem);
  const destinoFinal = colunaEhFinal(colunaDestino);
  const oportunidades = destinoFinal && !origemFinal ? card.oportunidades || [] : [];
  const exigeMotivoDaPerda = colunaDestino?.tipo === "encerrado" && !origemFinal;
  return {
    exigeModal: oportunidades.length > 0 || exigeMotivoDaPerda,
    exigeMotivoDaPerda,
    oportunidades,
  };
}

/** Mesmas regras do servidor: devolve a mensagem do problema ou "" se estiver tudo certo. */
export function validarColunas(colunas) {
  if (colunas.length < 2) return "Use pelo menos duas colunas.";
  if (colunas.length > MAXIMO_DE_COLUNAS) {
    return `O funil pode ter no máximo ${MAXIMO_DE_COLUNAS} colunas.`;
  }
  const nomes = new Set();
  for (const coluna of colunas) {
    const nome = String(coluna.nome || "").trim();
    if (!nome) return "Toda coluna precisa de um nome.";
    const chave = nome.toLocaleLowerCase("pt-BR");
    if (nomes.has(chave)) return `Já existe uma coluna chamada “${nome}”.`;
    nomes.add(chave);
  }
  if (!colunas.some((coluna) => coluna.tipo === "entrada")) {
    return "O funil precisa de uma coluna de entrada.";
  }
  if (!colunas.some((coluna) => coluna.tipo === "concluido")) {
    return "O funil precisa de uma coluna de concluído.";
  }
  return "";
}
