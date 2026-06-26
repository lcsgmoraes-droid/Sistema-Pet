export function parseDataLocal(valor) {
  if (!valor) return null;

  if (valor instanceof Date) {
    return new Date(valor.getFullYear(), valor.getMonth(), valor.getDate());
  }

  if (typeof valor === "string") {
    const dataBase = valor.includes("T") ? valor.split("T")[0] : valor;
    const match = dataBase.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (match) {
      const [, ano, mes, dia] = match;
      return new Date(Number(ano), Number(mes) - 1, Number(dia));
    }
  }

  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return null;
  return data;
}

export function parseDataHoraLocal(valor) {
  if (!valor) return null;
  if (valor instanceof Date) {
    return Number.isNaN(valor.getTime()) ? null : valor;
  }

  if (typeof valor === "string") {
    const match = valor.match(/^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})(?::(\d{2}))?/);
    if (match) {
      const [, ano, mes, dia, hora, minuto, segundo] = match;
      return new Date(
        Number(ano),
        Number(mes) - 1,
        Number(dia),
        Number(hora),
        Number(minuto),
        Number(segundo || 0),
      );
    }
  }

  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return null;
  return data;
}

export function dataKeyLocal(valor) {
  const data = parseDataLocal(valor);
  if (!data) return "";
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

export function calcularFiltroRapidoPeriodoVendas(filtro, dataBase = new Date()) {
  const agora = parseDataLocal(dataBase);
  if (!agora) return null;

  const ano = agora.getFullYear();
  const mes = String(agora.getMonth() + 1).padStart(2, "0");
  const hoje = dataKeyLocal(agora);

  switch (filtro) {
    case "hoje":
      return { inicio: hoje, fim: hoje };
    case "ontem": {
      const ontem = new Date(agora);
      ontem.setDate(agora.getDate() - 1);
      const dataOntem = dataKeyLocal(ontem);
      return { inicio: dataOntem, fim: dataOntem };
    }
    case "esta_semana": {
      const diaSemana = agora.getDay();
      const diasDesdeSegunda = diaSemana === 0 ? 6 : diaSemana - 1;
      const primeiroDia = new Date(agora);
      primeiroDia.setDate(agora.getDate() - diasDesdeSegunda);
      return { inicio: dataKeyLocal(primeiroDia), fim: hoje };
    }
    case "este_mes":
      return { inicio: `${ano}-${mes}-01`, fim: hoje };
    case "mes_anterior": {
      const mesPassado = new Date(ano, agora.getMonth() - 1, 1);
      const ultimoDia = new Date(ano, agora.getMonth(), 0);
      const anoMesPassado = mesPassado.getFullYear();
      const numeroMesPassado = String(mesPassado.getMonth() + 1).padStart(2, "0");
      return {
        inicio: `${anoMesPassado}-${numeroMesPassado}-01`,
        fim: dataKeyLocal(ultimoDia),
      };
    }
    case "ultimos_7_dias": {
      const seteDias = new Date(agora);
      seteDias.setDate(agora.getDate() - 7);
      return { inicio: dataKeyLocal(seteDias), fim: hoje };
    }
    case "ultimos_30_dias": {
      const trintaDias = new Date(agora);
      trintaDias.setDate(agora.getDate() - 30);
      return { inicio: dataKeyLocal(trintaDias), fim: hoje };
    }
    case "este_ano":
      return { inicio: `${ano}-01-01`, fim: hoje };
    default:
      return null;
  }
}

export function formatarDataLocal(valor, opcoes = {}) {
  const data = parseDataLocal(valor);
  if (!data) return "N/A";
  return data.toLocaleDateString("pt-BR", opcoes);
}

function adicionarDias(data, dias) {
  const proxima = new Date(data);
  proxima.setDate(proxima.getDate() + dias);
  return proxima;
}

export function listarDiasPeriodo(dataInicio, dataFim) {
  const inicio = parseDataLocal(dataInicio);
  const fim = parseDataLocal(dataFim);
  if (!inicio || !fim || inicio > fim) return [];

  const dias = [];
  for (let atual = new Date(inicio); atual <= fim; atual = adicionarDias(atual, 1)) {
    dias.push(new Date(atual));
  }
  return dias;
}

function calcularPascoa(ano) {
  const a = ano % 19;
  const b = Math.floor(ano / 100);
  const c = ano % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const mes = Math.floor((h + l - 7 * m + 114) / 31);
  const dia = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(ano, mes - 1, dia);
}

function feriadoMovel(ano, deslocamentoDias) {
  return dataKeyLocal(adicionarDias(calcularPascoa(ano), deslocamentoDias));
}

export function montarFeriadosPadrao(anos) {
  const feriados = {};
  anos.forEach((ano) => {
    Object.assign(feriados, {
      [`${ano}-01-01`]: "Confraternização Universal",
      [`${ano}-04-21`]: "Tiradentes",
      [`${ano}-05-01`]: "Dia do Trabalho",
      [`${ano}-09-07`]: "Independência do Brasil",
      [`${ano}-10-12`]: "Nossa Senhora Aparecida",
      [`${ano}-11-02`]: "Finados",
      [`${ano}-11-15`]: "Proclamação da República",
      [`${ano}-11-20`]: "Consciência Negra",
      [`${ano}-12-25`]: "Natal",
      [feriadoMovel(ano, -48)]: "Carnaval",
      [feriadoMovel(ano, -47)]: "Carnaval",
      [feriadoMovel(ano, -2)]: "Sexta-feira Santa",
      [feriadoMovel(ano, 60)]: "Corpus Christi",
    });
  });
  return feriados;
}

export function montarFeriadosPeriodoFinanceiro({
  dataInicio,
  dataFim,
  feriadosCustomizados = [],
}) {
  const anos = new Set(listarDiasPeriodo(dataInicio, dataFim).map((dia) => dia.getFullYear()));
  const feriados = montarFeriadosPadrao(Array.from(anos));

  feriadosCustomizados.forEach((feriado) => {
    if (feriado?.data) {
      feriados[feriado.data] = feriado.nome?.trim() || "Feriado cadastrado";
    }
  });

  return feriados;
}

export function montarVendasPorDataCalendarioFinanceiro({
  dataInicio,
  dataFim,
  vendasPorData = [],
  feriadosPorData = {},
  considerarSabadoDiaUtil = false,
}) {
  const vendasMap = new Map((vendasPorData || []).map((item) => [dataKeyLocal(item.data), item]));

  return listarDiasPeriodo(dataInicio, dataFim).map((dia) => {
    const key = dataKeyLocal(dia);
    const item = vendasMap.get(key) || {};
    const diaSemana = dia.getDay();
    const feriadoNome = feriadosPorData[key] || "";

    const quantidade = Number(item.quantidade || 0);
    const valorBruto = Number(item.valor_bruto || 0);
    const valorLiquido = Number(item.valor_liquido || 0);
    const temMovimento = quantidade > 0 || valorBruto > 0 || valorLiquido > 0;
    const sabado = diaSemana === 6;
    const domingo = diaSemana === 0;
    const sabadoUtil = sabado && considerarSabadoDiaUtil;
    const feriadoAberto = Boolean(feriadoNome && temMovimento);
    const fimDeSemana = domingo || (sabado && !sabadoUtil);
    const diaUtilBase = !domingo && (!sabado || sabadoUtil);
    const diaUtil = feriadoAberto || (diaUtilBase && !feriadoNome);

    return {
      data: key,
      quantidade,
      valor_bruto: valorBruto,
      taxa_entrega: Number(item.taxa_entrega || 0),
      desconto: Number(item.desconto || 0),
      percentual_desconto: Number(item.percentual_desconto || 0),
      valor_liquido: valorLiquido,
      valor_recebido: Number(item.valor_recebido || 0),
      saldo_aberto: Number(item.saldo_aberto || 0),
      ticket_medio: quantidade > 0 ? Number(item.ticket_medio || valorBruto / quantidade) : 0,
      dia_semana: formatarDataLocal(key, { weekday: "long" }),
      sabado,
      fim_de_semana: fimDeSemana,
      feriado_nome: feriadoNome,
      feriado_aberto: feriadoAberto,
      dia_util: diaUtil,
      sem_movimento: quantidade === 0 && valorLiquido === 0,
    };
  });
}

export function calcularResumoDiasPeriodoFinanceiro(vendasPorDataCalendario = []) {
  const diasUteis = vendasPorDataCalendario.filter((item) => item.dia_util);
  const diasTrabalhados = diasUteis.filter((item) => !item.sem_movimento);
  const diasUteisSemVenda = diasUteis.filter((item) => item.sem_movimento);
  const totalLiquidoDiasUteis = diasUteis.reduce(
    (sum, item) => sum + Number(item.valor_liquido || 0),
    0,
  );
  const totalLiquidoDiasTrabalhados = diasTrabalhados.reduce(
    (sum, item) => sum + Number(item.valor_liquido || 0),
    0,
  );

  return {
    totalDias: vendasPorDataCalendario.length,
    diasUteis: diasUteis.length,
    diasTrabalhados: diasTrabalhados.length,
    diasUteisSemVenda: diasUteisSemVenda.length,
    finsDeSemana: vendasPorDataCalendario.filter((item) => item.fim_de_semana).length,
    feriados: vendasPorDataCalendario.filter((item) => item.feriado_nome).length,
    mediaDiaUtil: diasUteis.length > 0 ? totalLiquidoDiasUteis / diasUteis.length : 0,
    mediaDiaTrabalhado:
      diasTrabalhados.length > 0 ? totalLiquidoDiasTrabalhados / diasTrabalhados.length : 0,
  };
}

export function getFeriadosStorageKey() {
  try {
    const tenant = JSON.parse(window.localStorage.getItem("selectedTenant") || "{}");
    return `financeiro:vendas:feriados-customizados:${tenant?.id || "global"}`;
  } catch {
    return "financeiro:vendas:feriados-customizados:global";
  }
}

export function carregarFeriadosCustomizados() {
  try {
    const salvo = window.localStorage.getItem(getFeriadosStorageKey());
    const parsed = salvo ? JSON.parse(salvo) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function getDiasUteisStorageKey() {
  try {
    const tenant = JSON.parse(window.localStorage.getItem("selectedTenant") || "{}");
    return `financeiro:vendas:dias-uteis:${tenant?.id || "global"}`;
  } catch {
    return "financeiro:vendas:dias-uteis:global";
  }
}

export function carregarConfigDiasUteis() {
  try {
    const salvo = window.localStorage.getItem(getDiasUteisStorageKey());
    const parsed = salvo ? JSON.parse(salvo) : {};
    return {
      considerarSabadoDiaUtil: Boolean(parsed?.considerarSabadoDiaUtil),
    };
  } catch {
    return { considerarSabadoDiaUtil: false };
  }
}
