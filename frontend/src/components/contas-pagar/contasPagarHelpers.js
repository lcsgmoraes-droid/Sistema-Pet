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
    data_inicio: hoje.data_inicio,
    data_fim: hoje.data_fim,
    apenas_vencidas: false,
    apenas_vencer: false,
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
