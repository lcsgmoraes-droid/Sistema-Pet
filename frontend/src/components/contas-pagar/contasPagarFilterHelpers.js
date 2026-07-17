export const PERIODOS_RAPIDOS_CONTAS_PAGAR = [
  { value: "hoje", label: "Hoje" },
  { value: "amanha", label: "Amanha" },
  { value: "semana", label: "Semana" },
  { value: "mes", label: "Mes" },
];

export function formatarDataISO(data) {
  const local = new Date(data.getTime() - data.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

export function calcularIntervaloPeriodoRapido(periodo) {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  const inicio = new Date(hoje);
  const fim = new Date(hoje);

  if (periodo === "amanha") {
    inicio.setDate(inicio.getDate() + 1);
    fim.setDate(fim.getDate() + 1);
  }

  if (periodo === "semana") {
    const diaSemana = hoje.getDay();
    const diffSegunda = diaSemana === 0 ? -6 : 1 - diaSemana;
    inicio.setDate(hoje.getDate() + diffSegunda);
    fim.setDate(inicio.getDate() + 6);
  }

  if (periodo === "mes") {
    inicio.setDate(1);
    fim.setMonth(hoje.getMonth() + 1, 0);
  }

  return {
    data_inicio: formatarDataISO(inicio),
    data_fim: formatarDataISO(fim),
  };
}

export function criarFiltrosPadraoContasPagar() {
  const hoje = calcularIntervaloPeriodoRapido("hoje");
  return {
    status: "todos",
    fornecedor_id: null,
    fornecedor_ids: [],
    fornecedor_modo: "incluir",
    data_inicio: hoje.data_inicio,
    data_fim: hoje.data_fim,
    apenas_vencidas: false,
    apenas_vencer: false,
    vence_hoje: false,
    numero_nf: "",
    tipo_custo: "todos",
    origem: "todos",
    busca: "",
    data_campo: "vencimento",
    fornecedor_busca: "",
    tipo_despesa_id: "",
    periodo_rapido: "hoje",
    ocultar_taxas_cartao: true,
    apenas_taxas_cartao: false,
  };
}

export function ehTaxaCartao(conta) {
  const texto = `${conta?.descricao || ""} ${conta?.documento || ""}`.toLowerCase();
  return (
    texto.includes("taxa credito") || texto.includes("taxa debito") || texto.includes("taxa cartao")
  );
}

export function extrairMensagemErroPagamento(error) {
  const detail = error?.response?.data?.detail ?? error?.response?.data?.message;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const mensagens = detail
      .map((item) => {
        const campo = Array.isArray(item?.loc)
          ? item.loc.filter((parte) => parte !== "body").join(".")
          : "";
        const mensagem = item?.msg || item?.message || item?.detail || String(item);

        if (campo.includes("data_pagamento")) {
          return "Data do pagamento e obrigatoria.";
        }

        if (campo.includes("valor_pago")) {
          return "Valor a pagar e obrigatorio.";
        }

        return campo ? `${campo}: ${mensagem}` : mensagem;
      })
      .filter(Boolean);

    if (mensagens.length > 0) {
      return mensagens.join(" ");
    }
  }

  if (detail && typeof detail === "object") {
    return detail.mensagem || detail.message || detail.erro || "Erro ao registrar pagamento";
  }

  return error?.message || "Erro ao registrar pagamento";
}

export function getFornecedorNome(fornecedor) {
  return fornecedor?.nome || fornecedor?.razao_social || fornecedor?.nome_fantasia || "";
}

export function montarParamsFiltrosContasPagar(filtrosParaAplicar = {}) {
  const params = new URLSearchParams();
  params.append("_t", Date.now());

  if (filtrosParaAplicar.status !== "todos") params.append("status", filtrosParaAplicar.status);
  if (filtrosParaAplicar.fornecedor_id)
    params.append("fornecedor_id", filtrosParaAplicar.fornecedor_id);
  if (Array.isArray(filtrosParaAplicar.fornecedor_ids)) {
    filtrosParaAplicar.fornecedor_ids.forEach((id) => params.append("fornecedor_ids", id));
  }
  if (filtrosParaAplicar.fornecedor_modo)
    params.append("fornecedor_modo", filtrosParaAplicar.fornecedor_modo);
  if (filtrosParaAplicar.data_inicio) params.append("data_inicio", filtrosParaAplicar.data_inicio);
  if (filtrosParaAplicar.data_fim) params.append("data_fim", filtrosParaAplicar.data_fim);
  if (filtrosParaAplicar.apenas_vencidas) params.append("apenas_vencidas", "true");
  if (filtrosParaAplicar.apenas_vencer) params.append("apenas_vencer", "true");
  if (filtrosParaAplicar.vence_hoje) params.append("vence_hoje", "true");
  if (filtrosParaAplicar.ocultar_taxas_cartao) params.append("ocultar_taxas_cartao", "true");
  if (filtrosParaAplicar.apenas_taxas_cartao) params.append("apenas_taxas_cartao", "true");
  if (filtrosParaAplicar.numero_nf) params.append("numero_nf", filtrosParaAplicar.numero_nf);
  if (filtrosParaAplicar.tipo_custo !== "todos")
    params.append("tipo_custo", filtrosParaAplicar.tipo_custo);
  if (filtrosParaAplicar.origem !== "todos") params.append("origem", filtrosParaAplicar.origem);
  if (filtrosParaAplicar.busca) params.append("busca", filtrosParaAplicar.busca);
  if (filtrosParaAplicar.fornecedor_busca)
    params.append("fornecedor_nome", filtrosParaAplicar.fornecedor_busca);
  if (filtrosParaAplicar.data_campo) params.append("data_campo", filtrosParaAplicar.data_campo);
  if (filtrosParaAplicar.tipo_despesa_id)
    params.append("tipo_despesa_id", filtrosParaAplicar.tipo_despesa_id);

  return params;
}

export function normalizarFormaPagamentoContasPagar(forma) {
  return {
    id: forma.id,
    nome: forma.nome,
    tipo: forma.tipo || forma.nome?.toLowerCase()?.replace(/\s+/g, "_") || "outro",
    icone: forma.icone || "Ã°Å¸â€™Â³",
    conta_bancaria_destino_id: forma.conta_bancaria_destino_id || null,
  };
}

export async function carregarFormasPagamentoContasPagar(api, safeArray) {
  const response = await api.get("/financeiro/formas-pagamento?apenas_ativas=true");
  return safeArray(response.data).map(normalizarFormaPagamentoContasPagar);
}

export function criarFiltrosDespesasCaixaContasPagar(filtrosPadrao, filtrosAtuais) {
  return {
    ...filtrosPadrao,
    status: "pago",
    origem: "caixa_pdv",
    data_campo: filtrosAtuais.data_campo || "pagamento",
    data_inicio: filtrosAtuais.data_inicio,
    data_fim: filtrosAtuais.data_fim,
    periodo_rapido: filtrosAtuais.periodo_rapido || "",
    ocultar_taxas_cartao: false,
    apenas_taxas_cartao: false,
  };
}

export function criarFiltrosTaxasCartaoContasPagar(filtrosPadrao, filtrosAtuais) {
  return {
    ...filtrosPadrao,
    data_inicio: filtrosAtuais.data_inicio,
    data_fim: filtrosAtuais.data_fim,
    data_campo: filtrosAtuais.data_campo || "vencimento",
    periodo_rapido: filtrosAtuais.periodo_rapido || "",
    ocultar_taxas_cartao: false,
    apenas_taxas_cartao: true,
  };
}

export function calcularValorFinalPagamentoContasPagar(dados = {}) {
  return (
    (Number(dados.valor_pago) || 0) +
    (Number(dados.valor_juros) || 0) +
    (Number(dados.valor_multa) || 0) -
    (Number(dados.valor_desconto) || 0)
  );
}
