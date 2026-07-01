export const formatarQuantidade = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor || 0));

export function fimDoMesIso() {
  const data = new Date();
  data.setMonth(data.getMonth() + 1, 0);
  return data.toISOString().split("T")[0];
}

export function inicioDoMesIso(dataBase = new Date()) {
  const data = new Date(dataBase);
  data.setDate(1);
  return data.toISOString().split("T")[0];
}

export function fimDoMesBaseIso(dataBase = new Date()) {
  const data = new Date(dataBase.getFullYear(), dataBase.getMonth() + 1, 0);
  return data.toISOString().split("T")[0];
}

export function hojeIso() {
  return new Date().toISOString().split("T")[0];
}

export function extrairListaProdutos(payload) {
  if (!payload) return [];
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.itens)) return payload.itens;
  if (Array.isArray(payload.produtos)) return payload.produtos;
  if (Array.isArray(payload.data)) return payload.data;
  if (Array.isArray(payload)) return payload;
  return [];
}

export function normalizarNumero(valor) {
  return Number(String(valor || "").replace(",", "."));
}

export function normalizarCodigo(valor) {
  return String(valor || "").replace(/\D/g, "");
}

export function produtoConfereCodigo(produto, termo) {
  const termoLimpo = String(termo || "")
    .trim()
    .toLowerCase();
  const termoDigitos = normalizarCodigo(termo);
  if (!termoLimpo) return false;
  const campos = [
    produto?.codigo,
    produto?.codigo_barras,
    produto?.gtin_ean,
    produto?.gtin_ean_tributario,
  ];
  return campos.some((campo) => {
    const texto = String(campo || "")
      .trim()
      .toLowerCase();
    if (!texto) return false;
    return texto === termoLimpo || (termoDigitos && normalizarCodigo(texto) === termoDigitos);
  });
}

export function formatarData(valor) {
  if (!valor) return "-";
  const data = new Date(`${valor}T00:00:00`);
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleDateString("pt-BR");
}

export function extrairObservacaoManualTransferencia(valor) {
  const texto = String(valor || "");
  const marcador = "\n\nItens:";
  const indice = texto.indexOf(marcador);
  if (indice >= 0) return texto.slice(0, indice).trim();
  return texto.trim();
}

export function criarFormTransferencia(overrides = {}) {
  return {
    tipo_operacao: "saida_parceiro",
    entrar_estoque: true,
    parceiro_id: "",
    data_vencimento: fimDoMesIso(),
    documento: "",
    observacao: "",
    ...overrides,
  };
}

export function criarFormBaixaTransferencia(overrides = {}) {
  const novaContaPagarAcerto = {
    descricao: "",
    valor: "",
    data_vencimento: hojeIso(),
    documento: "",
    observacao: "",
    ...(overrides.nova_conta_pagar_acerto || {}),
  };

  return {
    valor_recebido: "",
    data_recebimento: hojeIso(),
    modo_baixa: "recebimento",
    forma_pagamento_id: "",
    devolver_estoque: false,
    observacao: "",
    ...overrides,
    compensacoes: overrides.compensacoes || {},
    nova_conta_pagar_acerto: novaContaPagarAcerto,
  };
}

export function criarFiltrosHistoricoTransferencia(overrides = {}) {
  return {
    busca: "",
    status_filtro: "",
    data_inicio: "",
    data_fim: "",
    parceiro_id: "",
    ...overrides,
  };
}

export function montarFiltrosHistoricoTransferenciaParams(filtros = {}) {
  const params = {};

  if (filtros.parceiro_id) {
    params.parceiro_id = filtros.parceiro_id;
  } else if (filtros.busca?.trim()) {
    params.busca = filtros.busca.trim();
  }

  if (filtros.status_filtro) params.status_filtro = filtros.status_filtro;
  if (filtros.data_inicio) params.data_inicio = filtros.data_inicio;
  if (filtros.data_fim) params.data_fim = filtros.data_fim;

  return params;
}

export function criarHistoricoTransferenciasVazio(overrides = {}) {
  const { totais, ...rest } = overrides;
  return {
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    pages: 0,
    totais: {
      total_registros: 0,
      valor_total: 0,
      valor_recebido: 0,
      saldo_aberto: 0,
      pendentes: 0,
      recebidas: 0,
      vencidas: 0,
      ...(totais || {}),
    },
    ...rest,
  };
}

export function criarHistoricoEntradasParceiroVazio(overrides = {}) {
  const { totais, ...rest } = overrides;
  return {
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    pages: 0,
    totais: {
      total_registros: 0,
      valor_total: 0,
      valor_pago: 0,
      saldo_aberto: 0,
      pendentes: 0,
      pagas: 0,
      vencidas: 0,
      ...(totais || {}),
    },
    ...rest,
  };
}

export function criarItemTransferencia(produto, timestamp = Date.now()) {
  const custoUnitario = Number(produto?.preco_custo || 0);
  return {
    uid: `${produto.id}-${timestamp}`,
    produto_id: produto.id,
    produto_nome: produto.nome,
    codigo: produto.codigo,
    codigo_barras: produto.codigo_barras,
    estoque_atual: Number(produto?.estoque_atual || 0),
    custo_base_unitario: custoUnitario,
    custo_unitario: custoUnitario,
    quantidade: 1,
    total_item: custoUnitario,
  };
}

export function incrementarItemTransferencia(item, produto) {
  const novaQuantidade = Number(item.quantidade || 0) + 1;
  return {
    ...item,
    quantidade: novaQuantidade,
    total_item: novaQuantidade * Number(item.custo_unitario || 0),
    estoque_atual: Number(produto?.estoque_atual || item.estoque_atual || 0),
  };
}

export function criarItensEdicaoTransferencia(registro, timestamp = Date.now()) {
  return (Array.isArray(registro?.itens) ? registro.itens : []).map((item, index) => ({
    uid: `edit-${registro.conta_receber_id}-${item.produto_id}-${index}-${timestamp}`,
    produto_id: item.produto_id,
    produto_nome: item.produto_nome,
    codigo: item.codigo,
    codigo_barras: item.codigo_barras,
    estoque_atual: Number(item.estoque_atual || 0),
    custo_base_unitario: Number(item.custo_base_unitario ?? item.custo_unitario ?? 0),
    custo_unitario: Number(item.custo_unitario || 0),
    quantidade: Number(item.quantidade || 0),
    total_item: Number(item.valor_total || 0),
  }));
}

export function calcularDiferencaLancadaTransferencia(item = {}) {
  const quantidade = normalizarNumero(item.quantidade);
  const custoBase = normalizarNumero(item.custo_base_unitario ?? item.preco_custo);
  const valorUnitarioLancado = normalizarNumero(item.custo_unitario);
  const totalLancado =
    item.total_item === "" || item.total_item === null || item.total_item === undefined
      ? quantidade * valorUnitarioLancado
      : normalizarNumero(item.total_item);

  if (!Number.isFinite(quantidade) || !Number.isFinite(custoBase)) return 0;
  if (!Number.isFinite(totalLancado)) return 0;

  return Number((totalLancado - quantidade * custoBase).toFixed(2));
}

export function calcularTotalDiferencaLancadaTransferencia(itens = []) {
  const total = (Array.isArray(itens) ? itens : []).reduce(
    (acumulado, item) => acumulado + calcularDiferencaLancadaTransferencia(item),
    0,
  );
  return Number(total.toFixed(2));
}

export function montarPayloadTransferencia(parceiroId, form, itens) {
  return {
    parceiro_id: Number(parceiroId),
    data_vencimento: form.data_vencimento || undefined,
    documento: form.documento.trim() || undefined,
    observacao: form.observacao.trim() || undefined,
    itens: itens.map((item) => ({
      produto_id: Number(item.produto_id),
      quantidade: Number(item.quantidade),
      custo_unitario: Number(item.custo_unitario || 0),
      valor_total: Number(item.total_item || 0),
    })),
  };
}

export function montarEntradaParceiroPayload(parceiroId, form, itens) {
  const payload = {
    parceiro_id: Number(parceiroId),
    data_emissao: form.data_emissao || undefined,
    data_vencimento: form.data_vencimento || undefined,
    documento: form.documento?.trim() || undefined,
    observacao: form.observacao?.trim() || undefined,
    entrar_estoque: Boolean(form.entrar_estoque),
    itens: itens.map((item) => ({
      produto_id: Number(item.produto_id),
      quantidade: Number(item.quantidade),
      custo_unitario: Number(item.custo_unitario || 0),
      valor_total: Number(item.total_item || 0),
    })),
  };

  if (!payload.data_emissao) delete payload.data_emissao;
  if (!payload.data_vencimento) delete payload.data_vencimento;
  if (!payload.documento) delete payload.documento;
  if (!payload.observacao) delete payload.observacao;

  return payload;
}

export function montarCompensacoesBaixaPayload(compensacoes = {}) {
  return Object.entries(compensacoes)
    .map(([contaPagarId, valor]) => ({
      conta_pagar_id: Number(contaPagarId),
      valor_compensado: normalizarNumero(valor),
    }))
    .filter(
      (item) =>
        Number.isFinite(item.valor_compensado) &&
        item.valor_compensado > 0 &&
        item.conta_pagar_id > 0,
    );
}

export function montarBaixaTransferenciaPayload({
  form = {},
  valorRecebido,
  compensacoesPayload = [],
} = {}) {
  const modoBaixa = form.modo_baixa || "recebimento";
  const payload = {
    valor_recebido: valorRecebido,
    data_recebimento: form.data_recebimento || hojeIso(),
    modo_baixa: modoBaixa,
    compensacoes: modoBaixa === "acerto" ? compensacoesPayload : undefined,
  };

  if (modoBaixa === "recebimento" && form.forma_pagamento_id) {
    payload.forma_pagamento_id = Number(form.forma_pagamento_id);
  }
  if (form.observacao?.trim()) {
    payload.observacao = form.observacao.trim();
  }
  if (modoBaixa === "produto_devolvido") {
    payload.devolver_estoque = Boolean(form.devolver_estoque);
  }

  return payload;
}

export function distribuirBaixaTransferencias(valorBase, registros = [], ordem = "antiga") {
  let restante = normalizarNumero(valorBase);
  if (!Number.isFinite(restante) || restante <= 0) return {};

  const direcaoNova = ["nova", "mais_nova", "desc", "descendente"].includes(
    String(ordem || "")
      .trim()
      .toLowerCase(),
  );
  const ordenados = [...(Array.isArray(registros) ? registros : [])].sort((a, b) => {
    const dataA = String(a?.data_emissao || a?.data_vencimento || "");
    const dataB = String(b?.data_emissao || b?.data_vencimento || "");
    const comparacaoData = dataA.localeCompare(dataB);
    if (comparacaoData !== 0) return direcaoNova ? -comparacaoData : comparacaoData;
    const idA = Number(a?.conta_receber_id || 0);
    const idB = Number(b?.conta_receber_id || 0);
    return direcaoNova ? idB - idA : idA - idB;
  });

  const aplicacoes = {};
  ordenados.forEach((registro) => {
    if (restante <= 0) return;
    const contaId = Number(registro?.conta_receber_id || 0);
    const saldo = Number(registro?.saldo_aberto || 0);
    if (!contaId || saldo <= 0) return;

    const valorAplicado = Math.min(restante, saldo);
    if (valorAplicado > 0) {
      aplicacoes[contaId] = valorAplicado.toFixed(2);
      restante = Number((restante - valorAplicado).toFixed(2));
    }
  });

  return aplicacoes;
}

export function montarBaixaLoteTransferenciaPayload({
  parceiroId,
  form,
  aplicacoes = {},
  compensacoes = {},
}) {
  const compensacoesPayload = montarCompensacoesBaixaPayload(compensacoes);
  const novaContaPagarAcerto = form.nova_conta_pagar_acerto || {};
  const valorNovaContaPagar = normalizarNumero(novaContaPagarAcerto.valor);
  const payload = {
    parceiro_id: Number(parceiroId),
    modo_baixa: form.modo_baixa || "recebimento",
    data_recebimento: form.data_recebimento || hojeIso(),
    forma_pagamento_id:
      form.modo_baixa === "recebimento" && form.forma_pagamento_id
        ? Number(form.forma_pagamento_id)
        : undefined,
    observacao: form.observacao?.trim() || undefined,
    devolver_estoque: Boolean(form.devolver_estoque),
    aplicacoes: Object.entries(aplicacoes)
      .map(([contaReceberId, valor]) => ({
        conta_receber_id: Number(contaReceberId),
        valor_baixado: normalizarNumero(valor),
      }))
      .filter(
        (item) =>
          item.conta_receber_id > 0 &&
          Number.isFinite(item.valor_baixado) &&
          item.valor_baixado > 0,
      ),
    compensacoes: form.modo_baixa === "acerto" ? compensacoesPayload : [],
  };

  if (
    payload.modo_baixa === "acerto" &&
    Number.isFinite(valorNovaContaPagar) &&
    valorNovaContaPagar > 0
  ) {
    payload.nova_conta_pagar_acerto = {
      descricao: novaContaPagarAcerto.descricao?.trim() || undefined,
      valor: valorNovaContaPagar,
      data_vencimento: novaContaPagarAcerto.data_vencimento || form.data_recebimento || hojeIso(),
      documento: novaContaPagarAcerto.documento?.trim() || undefined,
      observacao: novaContaPagarAcerto.observacao?.trim() || undefined,
    };
    Object.keys(payload.nova_conta_pagar_acerto).forEach((chave) => {
      if (payload.nova_conta_pagar_acerto[chave] === undefined) {
        delete payload.nova_conta_pagar_acerto[chave];
      }
    });
  }

  if (!payload.forma_pagamento_id) delete payload.forma_pagamento_id;
  if (!payload.observacao) delete payload.observacao;

  return payload;
}

export function distribuirCompensacaoAutomatica(valorBase, contas = []) {
  let restante = normalizarNumero(valorBase);
  const proximaCompensacao = {};

  contas.forEach((conta) => {
    if (restante <= 0) {
      proximaCompensacao[conta.conta_pagar_id] = "";
      return;
    }

    const saldo = Number(conta.saldo_aberto || 0);
    const valorAplicado = Math.min(restante, saldo);
    proximaCompensacao[conta.conta_pagar_id] = valorAplicado > 0 ? valorAplicado.toFixed(2) : "";
    restante = Number((restante - valorAplicado).toFixed(2));
  });

  return proximaCompensacao;
}

export function obterErroAcertoTransferencia({
  modoBaixa,
  totalBaixa,
  totalCompensado,
  temCompensacao,
} = {}) {
  if (String(modoBaixa || "") !== "acerto") return null;
  if (!temCompensacao) {
    return "No acerto, selecione uma conta a pagar ou lance uma divida para compensar.";
  }
  if (Math.abs(normalizarNumero(totalCompensado) - normalizarNumero(totalBaixa)) > 0.01) {
    return "No acerto, o total compensado precisa bater com o total da baixa.";
  }
  return null;
}

function arredondarCentavos(valor) {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return 0;
  return Number(numero.toFixed(2));
}

export function calcularResumoEncontroContasParceiro({
  totalAplicado = 0,
  totalCompensado = 0,
  contasPagar = [],
} = {}) {
  const aplicado = arredondarCentavos(normalizarNumero(totalAplicado));
  const compensado = arredondarCentavos(normalizarNumero(totalCompensado));
  const contas = Array.isArray(contasPagar) ? contasPagar : [];
  const totalDisponivel = arredondarCentavos(
    contas.reduce((soma, conta) => soma + normalizarNumero(conta?.saldo_aberto), 0),
  );
  const totalDisponivelEntradas = arredondarCentavos(
    contas.reduce((soma, conta) => {
      if (conta?.origem_acerto !== "entrada_parceiro") return soma;
      return soma + normalizarNumero(conta?.saldo_aberto);
    }, 0),
  );
  const diferencaCompensacao = arredondarCentavos(aplicado - compensado);
  const saldoLiquidoDisponivel = arredondarCentavos(totalDisponivel - aplicado);
  const valorSugeridoAcerto = arredondarCentavos(Math.min(aplicado, totalDisponivel));
  const saldoReceberRemanescente = arredondarCentavos(Math.max(aplicado - valorSugeridoAcerto, 0));
  const saldoPagarRemanescente = arredondarCentavos(
    Math.max(totalDisponivel - valorSugeridoAcerto, 0),
  );
  const status =
    Math.abs(diferencaCompensacao) < 0.01
      ? "fechado"
      : diferencaCompensacao > 0
        ? "faltando"
        : "excedente";

  return {
    totalAplicado: aplicado,
    totalCompensado: compensado,
    totalDisponivel,
    totalDisponivelEntradas,
    diferencaCompensacao,
    saldoLiquidoDisponivel,
    valorSugeridoAcerto,
    saldoReceberRemanescente,
    saldoPagarRemanescente,
    status,
  };
}

export function baixarArquivoBlob(blob, nomeArquivo) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export const CUPOM_TRANSFERENCIA_WIDTH = 42;

export const COLUNAS_DOCUMENTO_TRANSFERENCIA = [
  { chave: "codigo", label: "Codigo / SKU" },
  { chave: "produto", label: "Descricao" },
  { chave: "quantidade", label: "Quantidade" },
  { chave: "custo_unitario", label: "Custo unitario" },
  { chave: "total", label: "Total do item" },
  { chave: "totais", label: "Totais do acerto" },
];

export const COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO = COLUNAS_DOCUMENTO_TRANSFERENCIA.map(
  (coluna) => coluna.chave,
);

export const COLUNAS_DOCUMENTO_TRANSFERENCIA_RETIRADA = ["codigo", "produto", "quantidade"];

export const COLUNAS_DOCUMENTO_TRANSFERENCIA_FINANCEIRAS = ["custo_unitario", "total", "totais"];

export const normalizarColunasDocumentoTransferencia = (
  colunas = COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
) => {
  const candidatas = Array.isArray(colunas) ? colunas : String(colunas || "").split(",");

  const selecionadas = new Set(
    candidatas
      .map((coluna) =>
        String(coluna || "")
          .trim()
          .toLowerCase(),
      )
      .filter(Boolean),
  );

  return COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO.filter((coluna) => selecionadas.has(coluna));
};

export const documentoTransferenciaTemValores = (colunas = []) =>
  normalizarColunasDocumentoTransferencia(colunas).some((coluna) =>
    COLUNAS_DOCUMENTO_TRANSFERENCIA_FINANCEIRAS.includes(coluna),
  );

export const montarParametrosDocumentoTransferencia = (colunas = []) => {
  const normalizadas = normalizarColunasDocumentoTransferencia(colunas);

  return {
    mostrar_codigo: normalizadas.includes("codigo"),
    mostrar_descricao: normalizadas.includes("produto"),
    mostrar_quantidade: normalizadas.includes("quantidade"),
    mostrar_custo_unitario: normalizadas.includes("custo_unitario"),
    mostrar_total_item: normalizadas.includes("total"),
    mostrar_totais: normalizadas.includes("totais"),
  };
};

function textoCupom(valor) {
  return String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\x20-\x7E]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function cortarCupom(valor, max = CUPOM_TRANSFERENCIA_WIDTH) {
  const limpo = textoCupom(valor);
  return limpo.length > max ? `${limpo.slice(0, max - 3)}...` : limpo;
}

function centralizarCupom(valor, width = CUPOM_TRANSFERENCIA_WIDTH) {
  const texto = cortarCupom(valor, width);
  const total = Math.max(0, width - texto.length);
  const esquerda = Math.floor(total / 2);
  return `${" ".repeat(esquerda)}${texto}${" ".repeat(total - esquerda)}`;
}

function parCupom(label, valor, width = CUPOM_TRANSFERENCIA_WIDTH) {
  const direita = cortarCupom(valor, Math.max(8, Math.floor(width / 2)));
  const maxEsquerda = Math.max(0, width - direita.length - 1);
  const esquerda = cortarCupom(label, maxEsquerda);
  return `${esquerda}${" ".repeat(Math.max(1, width - esquerda.length - direita.length))}${direita}`;
}

function quebrarCupom(valor, width = CUPOM_TRANSFERENCIA_WIDTH) {
  const palavras = textoCupom(valor).split(" ");
  const linhas = [];
  let atual = "";

  for (const palavra of palavras) {
    if (!palavra) continue;
    const proposta = atual ? `${atual} ${palavra}` : palavra;
    if (proposta.length <= width) {
      atual = proposta;
      continue;
    }

    if (atual) linhas.push(atual);
    if (palavra.length <= width) {
      atual = palavra;
      continue;
    }

    for (let i = 0; i < palavra.length; i += width) {
      linhas.push(palavra.slice(i, i + width));
    }
    atual = "";
  }

  if (atual) linhas.push(atual);
  return linhas.length ? linhas : [""];
}

function formatarMoedaCupom(valor) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(valor || 0);
}

export function montarCupomTransferencia(
  registro,
  colunasDocumento = COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
) {
  const colunas = normalizarColunasDocumentoTransferencia(colunasDocumento);
  const mostrarCodigo = colunas.includes("codigo");
  const mostrarProduto = colunas.includes("produto");
  const mostrarQuantidade = colunas.includes("quantidade");
  const mostrarCustoUnitario = colunas.includes("custo_unitario");
  const mostrarTotalItem = colunas.includes("total");
  const mostrarTotais = colunas.includes("totais");
  const documento = registro.documento || `TRP-${registro.conta_receber_id}`;
  const itens = Array.isArray(registro.itens) ? registro.itens : [];
  const linhas = [
    centralizarCupom("PET SHOP PRO"),
    centralizarCupom("TRANSFERENCIA PARCEIRO"),
    centralizarCupom("COMPROVANTE DE RETIRADA"),
    "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
    cortarCupom(`Documento: ${documento}`),
    cortarCupom(`Pessoa: ${registro.parceiro_nome || "-"}`),
    cortarCupom(`Emissao: ${formatarData(registro.data_emissao)}`),
    cortarCupom(`Vencimento: ${formatarData(registro.data_vencimento)}`),
    cortarCupom(`Status: ${registro.status_label || registro.status || "-"}`),
    "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
    "ITENS",
    "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
  ];

  for (const item of itens) {
    if (mostrarProduto) {
      linhas.push(...quebrarCupom(item.produto_nome || "Item"));
    }
    if (mostrarCodigo && mostrarQuantidade) {
      linhas.push(
        parCupom(
          `Cod ${item.codigo || item.produto_id || "-"}`,
          `Qtd ${formatarQuantidade(item.quantidade)}`,
        ),
      );
    } else if (mostrarCodigo) {
      linhas.push(cortarCupom(`Cod ${item.codigo || item.produto_id || "-"}`));
    } else if (mostrarQuantidade) {
      linhas.push(cortarCupom(`Qtd ${formatarQuantidade(item.quantidade)}`));
    }
    if (mostrarCustoUnitario) {
      linhas.push(parCupom("Custo un.", formatarMoedaCupom(item.custo_unitario)));
    }
    if (mostrarTotalItem) {
      linhas.push(parCupom("Total", formatarMoedaCupom(item.valor_total)));
    }
    linhas.push("");
  }

  if (mostrarTotais) {
    linhas.push(
      "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
      parCupom("Valor", formatarMoedaCupom(registro.valor_original)),
      parCupom("Recebido", formatarMoedaCupom(registro.valor_recebido)),
      parCupom("Saldo", formatarMoedaCupom(registro.saldo_aberto)),
      "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
    );
  } else {
    linhas.push("-".repeat(CUPOM_TRANSFERENCIA_WIDTH));
  }

  if (registro.observacoes) {
    linhas.push(
      "OBS:",
      ...quebrarCupom(registro.observacoes),
      "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
    );
  }

  linhas.push(
    "RETIRADO POR:",
    "",
    "Nome: ________________________________",
    "Doc.: ________________________________",
    "",
    "Assinatura:",
    "",
    "______________________________________",
    "",
    "Data: ____/____/________",
    "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
    centralizarCupom("Documento para controle interno"),
  );

  return linhas.join("\n");
}
