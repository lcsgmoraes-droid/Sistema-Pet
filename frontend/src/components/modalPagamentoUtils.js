import {
  campaignAllowsSaleChannel,
  getCashbackBonusParamKey,
} from "../utils/campaignChannelScope.js";

export const BANDEIRAS_CARTAO = [
  "Visa",
  "Mastercard",
  "Elo",
  "American Express",
  "Hipercard",
  "Hiper",
  "Cabal",
  "Diners Club",
  "Discover",
  "UnionPay",
  "Outros",
];

const BANDEIRA_POR_CODIGO = {
  visa: "Visa",
  mastercard: "Mastercard",
  elo: "Elo",
  amex: "American Express",
  hipercard: "Hipercard",
  hiper: "Hiper",
  cabal: "Cabal",
  diners: "Diners Club",
  discover: "Discover",
  unionpay: "UnionPay",
  outros: "Outros",
};

export function normalizarBandeiraCartao(bandeira = "") {
  const valor = String(bandeira || "")
    .trim()
    .toLowerCase();
  if (valor === "master" || valor === "master card") return "mastercard";
  if (valor === "american express") return "amex";
  if (valor === "diners club") return "diners";
  if (valor === "union pay") return "unionpay";
  if (valor === "outro" || valor === "outras" || valor === "outra") return "outros";
  return valor;
}

export function obterModalidadeCartao(formaPagamento = null) {
  const tipo = String(formaPagamento?.tipo_cartao || formaPagamento?.tipo || "").toLowerCase();
  const nome = String(formaPagamento?.nome || "").toLowerCase();
  if (tipo.includes("debito") || tipo.includes("débito") || nome.includes("débito")) {
    return "debito";
  }
  if (tipo.includes("credito") || tipo.includes("crédito") || nome.includes("crédito")) {
    return "credito";
  }
  if (tipo.includes("voucher") || nome.includes("voucher")) return "voucher";
  return "";
}

export function ehFormaPagamentoCartao(formaPagamento = null) {
  return Boolean(obterModalidadeCartao(formaPagamento));
}

export function obterBandeirasDisponiveis({ taxas = [], modalidade = "" } = {}) {
  const regrasModalidade = (taxas || []).filter((taxa) => taxa.modalidade === modalidade);
  if (!regrasModalidade.length) return taxas.length ? [] : BANDEIRAS_CARTAO;

  const codigosExatos = [...new Set(regrasModalidade.map((taxa) => taxa.bandeira))].filter(
    (codigo) => codigo !== "outros",
  );
  if (!codigosExatos.length) return BANDEIRAS_CARTAO;
  return codigosExatos.map((codigo) => BANDEIRA_POR_CODIGO[codigo] || codigo);
}

export function obterParcelasDisponiveis({
  taxas = [],
  modalidade = "",
  bandeira = "",
  maxParcelas = 12,
} = {}) {
  const limite = modalidade === "debito" ? 1 : Math.max(1, Number(maxParcelas || 1));
  const regrasModalidade = (taxas || []).filter((taxa) => taxa.modalidade === modalidade);
  if (!regrasModalidade.length) {
    if (taxas.length) return [];
    return Array.from({ length: limite }, (_, index) => index + 1);
  }

  const codigoBandeira = normalizarBandeiraCartao(bandeira);
  if (!codigoBandeira) return [];
  return [
    ...new Set(
      regrasModalidade
        .filter((taxa) => [codigoBandeira, "outros"].includes(taxa.bandeira))
        .map((taxa) => Number(taxa.parcelas)),
    ),
  ]
    .filter((parcela) => parcela >= 1 && parcela <= limite)
    .sort((a, b) => a - b);
}

export function obterParcelasPermitidasParaForma(formaPagamento = null) {
  if (formaPagamento?.tipo === "crediario") {
    return Array.from({ length: 60 }, (_, index) => index + 1);
  }

  const limite = Math.max(1, Number(formaPagamento?.parcelas_maximas || 12));
  return Array.from({ length: limite }, (_, index) => index + 1);
}

export function obterBandeiraPadraoPdv({ operadora = null, bandeiras = [] } = {}) {
  const padrao = normalizarBandeiraCartao(operadora?.bandeira_padrao);
  const correspondente = bandeiras.find(
    (bandeira) => normalizarBandeiraCartao(bandeira) === padrao,
  );
  if (correspondente) return correspondente;
  return bandeiras.length === 1 ? bandeiras[0] : "";
}

export function obterTaxaCartaoSelecionada({
  taxas = [],
  modalidade = "",
  bandeira = "",
  parcelas = 1,
} = {}) {
  const codigo = normalizarBandeiraCartao(bandeira);
  const candidatas = (taxas || []).filter(
    (taxa) =>
      taxa.modalidade === modalidade &&
      Number(taxa.parcelas) === Number(parcelas) &&
      [codigo, "outros"].includes(taxa.bandeira),
  );
  return candidatas.find((taxa) => taxa.bandeira === codigo) || candidatas[0] || null;
}

export function identificarIconeFormaPagamento(icone, nome) {
  const key = String(icone || nome || "").toLowerCase();
  if (key.includes("pix")) return "qr_code";
  if (key.includes("dinheiro") || key.includes("cash")) return "banknote";
  if (key.includes("debito") || key.includes("débito")) return "credit_card";
  if (key.includes("parcelado")) return "credit_card";
  if (key.includes("credito") || key.includes("crédito")) return "credit_card";
  if (key.includes("transfer") || key.includes("banc")) return "transfer";
  if (key.includes("boleto")) return "receipt";
  if (key.includes("wallet") || key.includes("carteira")) return "wallet";
  return "credit_card";
}

export function ehFormaPagamentoPix(formaPagamento = null) {
  return String(formaPagamento?.nome || "")
    .toLowerCase()
    .includes("pix");
}

export function mapearTipoPagamentoStonePos(formaPagamento = null) {
  void formaPagamento;
  return null;
}

export function ehFormaPagamentoStonePos(formaPagamento = null) {
  return Boolean(mapearTipoPagamentoStonePos(formaPagamento));
}

export function podeEnviarPagamentoStonePos({
  formaPagamento = null,
  pagamentos = [],
  totalPagoExistente = 0,
  valorRestante = 0,
  stonePedidoPendente = false,
} = {}) {
  void formaPagamento;
  void pagamentos;
  void totalPagoExistente;
  void valorRestante;
  void stonePedidoPendente;
  return {
    podeEnviar: false,
    motivo: "Integracao Stone POS descontinuada.",
  };
}

export function calcularCustoTotalItensVenda(itens = []) {
  return (itens || []).reduce(
    (sum, item) => sum + Number(item?.custo || 0) * Number(item?.quantidade || 1),
    0,
  );
}

export function montarVendaParaPersistirComCupom({ venda = {}, cupomParaFinalizar = null }) {
  if (!cupomParaFinalizar) return venda;

  return {
    ...venda,
    cupom_code: cupomParaFinalizar.code,
    cupom_discount_applied: cupomParaFinalizar.discount_applied,
  };
}

export async function persistirVendaAbertaParaPagamento({
  vendaParaPersistir = {},
  payloadVenda = {},
  vendaIdPersistida = null,
  criarVenda,
  atualizarVenda,
}) {
  const vendaId = vendaParaPersistir.id || vendaIdPersistida;

  if (vendaId) {
    await atualizarVenda(vendaId, payloadVenda);
    return vendaId;
  }

  const vendaCriada = await criarVenda(payloadVenda);
  if (!vendaCriada?.id) {
    throw new Error("A venda foi criada sem retornar um identificador");
  }

  return vendaCriada.id;
}

export function devePerguntarNotaFiscal(resultado = {}) {
  return resultado?.status === "finalizada" || resultado?.status === "pago_nf";
}

export function extrairCorIndicadorMargem(resposta = {}) {
  return resposta?.resultado?.cor_indicador || null;
}

export function obterCorParcelamentoAtual({
  formaPagamento = null,
  simulacoesParcelamento = {},
  numeroParcelas = 1,
}) {
  if (!formaPagamento?.permite_parcelamento) return "verde";
  return simulacoesParcelamento[formaPagamento.id]?.[numeroParcelas]?.cor ?? "verde";
}

export function obterCorVisualParcelamento({
  formaPagamento = null,
  simulacoesParcelamento = {},
  numeroParcelas = 1,
  statusMargem = "verde",
}) {
  return (
    simulacoesParcelamento[formaPagamento?.id]?.[numeroParcelas]?.cor || statusMargem || "verde"
  );
}

export function obterEstiloVisualParcelamento(cor = "verde") {
  if (cor === "vermelho") {
    return {
      selectClass: "border-red-400 bg-red-50 text-red-900",
      painelClass: "bg-red-50 border-red-300",
      tituloClass: "text-red-800",
      descricaoClass: "text-red-700",
      optionClass: "bg-red-100 text-red-900",
      prefixo: "\uD83D\uDEAB ",
      aviso: " - Requer justificativa",
    };
  }

  if (cor === "amarelo") {
    return {
      selectClass: "border-yellow-400 bg-yellow-50 text-yellow-900",
      painelClass: "bg-yellow-50 border-yellow-300",
      tituloClass: "text-yellow-800",
      descricaoClass: "text-yellow-700",
      optionClass: "bg-yellow-100 text-yellow-900",
      prefixo: "\u26A0\uFE0F ",
      aviso: " - Requer aten\u00E7\u00E3o",
    };
  }

  return {
    selectClass: "border-gray-300 bg-white",
    painelClass: "bg-blue-50 border-blue-200",
    tituloClass: "text-blue-800",
    descricaoClass: "text-blue-600",
    optionClass: "",
    prefixo: "",
    aviso: "",
  };
}

export function avaliarEstadoJustificativaMargem({
  statusMargem = null,
  corParcelamentoAtual = "verde",
  justificativaTexto = "",
}) {
  const margemCriticaAtual = statusMargem === "vermelho" || corParcelamentoAtual === "vermelho";

  return {
    margemCriticaAtual,
    mostrarCampoJustificativa:
      margemCriticaAtual || Boolean(justificativaTexto && justificativaTexto.trim().length > 0),
  };
}

export function calcularResumoRecebimento({
  valorTotal = 0,
  pagamentos = [],
  totalPagoExistente = 0,
  valorRecebido = 0,
}) {
  const total = Number(valorTotal || 0);
  const pagoExistente = Number(totalPagoExistente || 0);
  const pagoNovo = pagamentos.reduce((sum, pagamento) => sum + Number(pagamento.valor || 0), 0);
  const valorPago = pagoNovo + pagoExistente;
  const valorRestante = Math.max(0, total - valorPago);
  const vendaQuitadaComPagamentosExistentes = pagoExistente >= total - 0.01;

  return {
    valorPago,
    valorRestante,
    vendaQuitadaComPagamentosExistentes,
    podeConfirmarFinalizacao: pagamentos.length > 0 || vendaQuitadaComPagamentosExistentes,
    troco: Number(valorRecebido || 0) > 0 ? Number(valorRecebido || 0) - valorRestante : 0,
  };
}

export function montarCupomParaFinalizar({ cupomAplicado, venda = {} }) {
  if (cupomAplicado) return cupomAplicado;
  if (!venda.cupom_code) return null;

  return {
    code: venda.cupom_code,
    discount_applied: venda.cupom_discount_applied ?? venda.desconto_valor ?? null,
  };
}

export function descreverCupomMargem(cupomParaFinalizar, formatarValor = (valor) => String(valor)) {
  if (!cupomParaFinalizar?.code || Number(cupomParaFinalizar?.discount_applied || 0) <= 0) {
    return "";
  }

  return `A margem ficou baixa por conta do cupom ${String(cupomParaFinalizar.code).toUpperCase()} (${formatarValor(Number(cupomParaFinalizar.discount_applied || 0))} de desconto).`;
}

export function montarObservacoesComJustificativaMargem({
  observacoesAtuais = "",
  descricaoCupomMargem = "",
  justificativaTexto = "",
}) {
  const justificativaFinal = descricaoCupomMargem
    ? `${descricaoCupomMargem} Observacao informada: ${justificativaTexto}`
    : justificativaTexto;
  const blocoJustificativa = `JUSTIFICATIVA (Margem Critica): ${justificativaFinal}`;

  if (String(observacoesAtuais || "").includes(blocoJustificativa)) {
    return observacoesAtuais || "";
  }

  return observacoesAtuais ? `${observacoesAtuais}\n\n${blocoJustificativa}` : blocoJustificativa;
}

export function vencimentoPadraoCrediario(dias = 30) {
  const data = new Date();
  data.setDate(data.getDate() + dias);
  const dia = String(data.getDate()).padStart(2, "0");
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  return `${dia}-${mes}-${data.getFullYear()}`;
}

export function mascararDataCrediario(valor = "") {
  const digitos = String(valor).replace(/\D/g, "").slice(0, 8);
  if (digitos.length <= 2) return digitos;
  if (digitos.length <= 4) return `${digitos.slice(0, 2)}-${digitos.slice(2)}`;
  return `${digitos.slice(0, 2)}-${digitos.slice(2, 4)}-${digitos.slice(4)}`;
}

export function dataCrediarioParaIso(valor = "") {
  const correspondencia = String(valor).match(/^(\d{2})-(\d{2})-(\d{4})$/);
  if (!correspondencia) return null;
  const [, dia, mes, ano] = correspondencia;
  const data = new Date(Number(ano), Number(mes) - 1, Number(dia));
  if (
    data.getFullYear() !== Number(ano) ||
    data.getMonth() !== Number(mes) - 1 ||
    data.getDate() !== Number(dia)
  ) {
    return null;
  }
  return `${ano}-${mes}-${dia}`;
}

export function gerarPlanoCrediario({
  valorTotal = 0,
  numeroParcelas = 1,
  primeiraData = "",
  intervalo = "mensal",
} = {}) {
  const dataIso = dataCrediarioParaIso(primeiraData);
  const quantidade = Math.trunc(Number(numeroParcelas || 0));
  if (!dataIso || quantidade < 1 || quantidade > 60) return [];
  if (quantidade > 1 && !["7_dias", "15_dias", "mensal"].includes(intervalo)) return [];

  const [ano, mes, dia] = dataIso.split("-").map(Number);
  const primeira = new Date(ano, mes - 1, dia, 12);
  const totalCentavos = Math.round(Number(valorTotal || 0) * 100);
  const valorBaseCentavos = Math.round(totalCentavos / quantidade);

  return Array.from({ length: quantidade }, (_, indice) => {
    let vencimento;
    if (intervalo === "7_dias" || intervalo === "15_dias") {
      vencimento = new Date(primeira);
      vencimento.setDate(primeira.getDate() + (intervalo === "7_dias" ? 7 : 15) * indice);
    } else {
      const indiceMes = ano * 12 + (mes - 1) + indice;
      const anoParcela = Math.floor(indiceMes / 12);
      const mesParcela = indiceMes % 12;
      const ultimoDia = new Date(anoParcela, mesParcela + 1, 0, 12).getDate();
      vencimento = new Date(anoParcela, mesParcela, Math.min(dia, ultimoDia), 12);
    }

    const valorCentavos =
      indice === quantidade - 1
        ? totalCentavos - valorBaseCentavos * (quantidade - 1)
        : valorBaseCentavos;
    return {
      numero: indice + 1,
      total_parcelas: quantidade,
      valor: valorCentavos / 100,
      data_vencimento: `${String(vencimento.getDate()).padStart(2, "0")}-${String(
        vencimento.getMonth() + 1,
      ).padStart(2, "0")}-${vencimento.getFullYear()}`,
    };
  });
}

export function montarPagamentoRecebido({
  formaPagamento,
  valor = 0,
  valorRestante = 0,
  bandeira = "",
  nsuCartao = "",
  operadora = null,
  numeroParcelas = 1,
  troco = 0,
}) {
  const tipo = formaPagamento?.tipo;
  const isCartao = ["cartao_credito", "cartao_debito"].includes(tipo);
  const parcelas =
    tipo === "crediario" || formaPagamento?.permite_parcelamento ? numeroParcelas : 1;
  const formaPagamentoId = normalizarFormaPagamentoId(formaPagamento?.id);
  const dataVencimentoCrediario =
    tipo === "crediario" ? dataCrediarioParaIso(formaPagamento?.data_vencimento_crediario) : null;

  return {
    forma_pagamento: formaPagamento.nome,
    forma_pagamento_tipo: tipo,
    forma_id: formaPagamento.id,
    forma_pagamento_id: formaPagamentoId,
    nome: formaPagamento.nome,
    valor: Math.min(Number(valor || 0), Number(valorRestante || 0)),
    bandeira: isCartao ? bandeira : null,
    nsu_cartao: isCartao && nsuCartao ? nsuCartao : null,
    operadora_id: isCartao ? operadora?.id || null : null,
    modalidade_cartao: isCartao ? obterModalidadeCartao(formaPagamento) : null,
    numero_parcelas: parcelas,
    parcelas,
    valor_recebido: Number(valor || 0),
    troco: tipo === "dinheiro" && troco > 0 ? troco : null,
    is_credito_cliente: formaPagamento.nome === "Crédito Cliente" || tipo === "credito_cliente",
    is_cashback: formaPagamento.id === "cashback",
    ...(dataVencimentoCrediario
      ? {
          data_recebimento_prevista: dataVencimentoCrediario,
          prazo_recebimento_dias: Math.max(
            0,
            Math.ceil(
              (new Date(`${dataVencimentoCrediario}T12:00:00`).getTime() - Date.now()) / 86400000,
            ),
          ),
          intervalo_crediario:
            parcelas > 1 ? formaPagamento?.intervalo_crediario || "mensal" : null,
        }
      : {}),
  };
}

export function validarPagamentoParaAdicionar({
  formaPagamento,
  valor = 0,
  saldoCashback = 0,
  bandeira = "",
  operadora = null,
  numeroParcelas = 1,
  parcelasDisponiveis = [],
  cliente = null,
}) {
  if (!formaPagamento) {
    return "Selecione uma forma de pagamento";
  }

  const valorNumerico = Number(valor || 0);

  if (valorNumerico <= 0) {
    return "Informe o valor recebido";
  }

  if (formaPagamento.tipo === "crediario" && !cliente?.id) {
    return "Selecione o cliente da venda para usar o crediário";
  }

  if (
    formaPagamento.tipo === "crediario" &&
    !dataCrediarioParaIso(formaPagamento.data_vencimento_crediario)
  ) {
    return "Informe uma data de vencimento válida no formato DD-MM-AAAA";
  }

  if (formaPagamento.tipo === "crediario") {
    const dataIso = dataCrediarioParaIso(formaPagamento.data_vencimento_crediario);
    const hoje = new Date();
    const hojeIso = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(
      hoje.getDate(),
    ).padStart(2, "0")}`;
    if (dataIso && dataIso < hojeIso) {
      return "A primeira data do crediário não pode estar no passado";
    }
    if (!Number.isInteger(numeroParcelas) || numeroParcelas < 1 || numeroParcelas > 60) {
      return "Informe uma quantidade entre 1 e 60 parcelas";
    }
    if (
      numeroParcelas > 1 &&
      !["7_dias", "15_dias", "mensal"].includes(formaPagamento.intervalo_crediario)
    ) {
      return "Escolha o intervalo entre as parcelas do crediário";
    }
  }

  if (
    formaPagamento.id === "credito_cliente" &&
    valorNumerico > Number(formaPagamento.credito_disponivel || 0)
  ) {
    return `Valor excede o crédito disponível (R$ ${Number(
      formaPagamento.credito_disponivel || 0,
    ).toFixed(2)})`;
  }

  if (formaPagamento.id === "cashback" && valorNumerico > Number(saldoCashback || 0) + 0.01) {
    return `Valor excede o cashback disponível (R$ ${Number(saldoCashback || 0)
      .toFixed(2)
      .replace(".", ",")})`;
  }

  const isCartao = ["cartao_credito", "cartao_debito"].includes(formaPagamento.tipo);

  if (isCartao && !bandeira) {
    return "Selecione a bandeira do cartão";
  }

  if (isCartao && !operadora) {
    return "Selecione a operadora do cartão";
  }

  if (operadora && numeroParcelas > operadora.max_parcelas) {
    return `A operadora ${operadora.nome} permite no máximo ${operadora.max_parcelas}x`;
  }

  if (isCartao && parcelasDisponiveis.length && !parcelasDisponiveis.includes(numeroParcelas)) {
    return "Nao existe taxa cadastrada para a parcela escolhida";
  }

  if (isCartao && bandeira && operadora?.taxas_configuradas > 0 && !parcelasDisponiveis.length) {
    return "Nao existe taxa cadastrada para essa operadora, bandeira e modalidade";
  }

  return "";
}

export function montarItensAnaliseMargem(itens = []) {
  return (itens || []).map((item) => ({
    produto_id: item.produto_id,
    quantidade: item.quantidade,
    preco_venda: item.preco_unitario || item.preco_venda || 0,
    custo: item.custo || null,
  }));
}

export function montarPagamentoAVista(valor, formaPagamentoId = 1) {
  return [
    {
      forma_pagamento_id: formaPagamentoId,
      valor,
      parcelas: 1,
    },
  ];
}

export function montarPagamentoSimuladoParcelamento({
  formaPagamentoId,
  valorTotal = 0,
  parcelas = 1,
  operadoraId = null,
  bandeira = "",
  modalidade = "",
}) {
  return [
    {
      forma_pagamento_id: formaPagamentoId,
      valor: Number(valorTotal || 0),
      parcelas,
      operadora_id: operadoraId,
      bandeira: bandeira || null,
      modalidade: modalidade || null,
    },
  ];
}

export function normalizarResultadoSimulacaoParcelamento(resposta = {}) {
  const corIndicador = extrairCorIndicadorMargem(resposta);
  if (!corIndicador) return null;

  return {
    cor: corIndicador,
    classificacao: corIndicador,
  };
}

export function montarFallbackSimulacaoParcelamento() {
  return { cor: null, classificacao: "verde" };
}

export function montarPagamentosMargem({ pagamentosExistentes = [], pagamentos = [] }) {
  return [...pagamentosExistentes, ...pagamentos.filter((pagamento) => !pagamento.is_cashback)];
}

export function montarPayloadAnaliseMargem({ venda = {}, formasPagamento = [] }) {
  return {
    items: montarItensAnaliseMargem(venda.itens || []),
    formas_pagamento: formasPagamento,
    desconto: venda.desconto_valor || 0,
    taxa_entrega: venda.entrega?.taxa_entrega_total || 0,
    vendedor_id: venda.funcionario_id || null,
  };
}

export function montarItensParaVerificarEstoqueNegativo(itens = []) {
  return (itens || [])
    .filter((item) => item.tipo === "produto" && item.produto_id)
    .map((item) => ({
      produto_id: item.produto_id,
      quantidade: item.quantidade,
    }));
}

export function montarMensagemEstoqueNegativo(produtosNegativos = []) {
  const mensagens = (produtosNegativos || [])
    .map(
      (produto) =>
        `\u2022 ${produto.produto_nome}: estoque atual ${produto.estoque_atual}, ap\u00F3s venda ficar\u00E1 ${produto.estoque_resultante}`,
    )
    .join("\n");

  return `\u26A0\uFE0F ATEN\u00C7\u00C3O: Os seguintes produtos ficar\u00E3o com ESTOQUE NEGATIVO:\n\n${mensagens}\n\nDeseja continuar mesmo assim?`;
}

export function montarFormasPagamentoAnalise({
  pagamentos = [],
  formasPagamento = [],
  valorTotal = 0,
}) {
  const totalAlocado = pagamentos.reduce((sum, pagamento) => sum + Number(pagamento.valor || 0), 0);
  const restante = Number(valorTotal || 0) - totalAlocado;
  const dinheiro = formasPagamento.find(
    (forma) =>
      forma.tipo === "dinheiro" ||
      String(forma.nome || "")
        .toLowerCase()
        .includes("dinheiro"),
  );
  const dinheiroId = normalizarFormaPagamentoId(dinheiro?.id);

  if (pagamentos.length === 0) {
    return dinheiroId ? montarPagamentoAVista(Number(valorTotal || 0), dinheiroId) : [];
  }

  const formasAnalise = pagamentos.flatMap((pagamento) => {
    const formaPagamentoId = resolverFormaPagamentoIdAnalise(pagamento, formasPagamento);
    if (!formaPagamentoId) return [];

    return [
      {
        forma_pagamento_id: formaPagamentoId,
        valor: pagamento.valor,
        parcelas: pagamento.parcelas || pagamento.numero_parcelas || 1,
        operadora_id: pagamento.operadora_id || null,
        bandeira: pagamento.bandeira || null,
        modalidade: pagamento.modalidade || pagamento.modalidade_cartao || null,
      },
    ];
  });

  if (restante > 0 && dinheiroId) {
    formasAnalise.push({
      forma_pagamento_id: dinheiroId,
      valor: restante,
      parcelas: 1,
    });
  }

  return formasAnalise;
}

function normalizarFormaPagamentoId(valor) {
  if (typeof valor === "number" && Number.isInteger(valor) && valor > 0) {
    return valor;
  }

  if (typeof valor === "string" && /^\d+$/.test(valor.trim())) {
    const id = Number(valor);
    return id > 0 ? id : null;
  }

  return null;
}

function resolverFormaPagamentoIdAnalise(pagamento = {}, formasPagamento = []) {
  const idDireto = normalizarFormaPagamentoId(pagamento.forma_pagamento_id ?? pagamento.forma_id);
  if (idDireto) return idDireto;

  const nomePagamento = String(pagamento.forma_pagamento || pagamento.nome || "")
    .trim()
    .toLocaleLowerCase("pt-BR");
  if (!nomePagamento) return null;

  const formaCorrespondente = formasPagamento.find(
    (forma) =>
      String(forma.nome || "")
        .trim()
        .toLocaleLowerCase("pt-BR") === nomePagamento,
  );

  return normalizarFormaPagamentoId(formaCorrespondente?.id);
}

export function calcularFaixasParcelamento(simulacoes, maxParcelas) {
  const faixas = {
    saudavel: { min: 1, max: 0 },
    alerta: { min: 0, max: 0 },
    proibido: { min: 0, max: maxParcelas },
  };

  let ultimaVerde = 0;
  let primeiraVermelha = maxParcelas + 1;

  for (let i = 1; i <= maxParcelas; i += 1) {
    const sim = simulacoes[i];
    if (!sim) continue;

    if (sim.cor === "verde") {
      ultimaVerde = i;
    } else if (sim.cor === "vermelho" && i < primeiraVermelha) {
      primeiraVermelha = i;
    }
  }

  faixas.saudavel.max = ultimaVerde;
  faixas.alerta.min = ultimaVerde + 1;
  faixas.alerta.max = primeiraVermelha - 1;
  faixas.proibido.min = primeiraVermelha;

  return faixas;
}

export function resolverFaixasParcelamentoDaForma({
  formaPagamentoSelecionada = null,
  simulacoesParcelamento = {},
  formasPagamento = [],
}) {
  if (formaPagamentoSelecionada?.permite_parcelamento) {
    const simulacoesExistentes = simulacoesParcelamento[formaPagamentoSelecionada.id];

    if (!simulacoesExistentes) {
      return {
        acao: "simular",
        formaPagamento: formaPagamentoSelecionada,
        faixas: null,
      };
    }

    return {
      acao: "usar_existente",
      formaPagamento: formaPagamentoSelecionada,
      faixas: calcularFaixasParcelamento(
        simulacoesExistentes,
        formaPagamentoSelecionada?.parcelas_maximas ?? 12,
      ),
    };
  }

  if (formaPagamentoSelecionada) return null;

  const primeiraFormaComParcelamento = Object.keys(simulacoesParcelamento)[0];
  if (!primeiraFormaComParcelamento || formasPagamento.length === 0) {
    return null;
  }

  const formaInfo = formasPagamento.find(
    (forma) => forma.id === Number(primeiraFormaComParcelamento),
  );
  if (!formaInfo) return null;

  return {
    acao: "usar_existente",
    formaPagamento: formaInfo,
    faixas: calcularFaixasParcelamento(
      simulacoesParcelamento[primeiraFormaComParcelamento],
      formaInfo?.parcelas_maximas ?? 12,
    ),
  };
}

export function calcularBeneficiosCampanhaPreview({
  campanhasCompra = [],
  rankCliente = "bronze",
  canalVenda = "loja_fisica",
  valorBase = 0,
}) {
  const valorBaseNumerico = Number(valorBase || 0);
  const canal = canalVenda || "loja_fisica";
  const assinaturasVistas = new Set();
  const campanhasElegiveisCanal = campanhasCompra.filter((campanha) => {
    if (!campaignAllowsSaleChannel(campanha, canal)) return false;

    const paramsOrdenados = Object.fromEntries(
      Object.entries(campanha.params || {}).sort(([chaveA], [chaveB]) =>
        chaveA.localeCompare(chaveB),
      ),
    );
    const assinatura = JSON.stringify([campanha.campaign_type, campanha.name, paramsOrdenados]);
    if (assinaturasVistas.has(assinatura)) return false;
    assinaturasVistas.add(assinatura);
    return true;
  });

  const cashbackPrevisto = campanhasElegiveisCanal
    .filter((campanha) => campanha.campaign_type === "cashback")
    .map((campanha) => {
      const params = campanha.params || {};
      const chaveRank = `${rankCliente}_percent`;
      const percentualBase = Number(params[chaveRank] ?? params.bronze_percent ?? 0);
      const bonusCanal = Number(params[getCashbackBonusParamKey(canal)] ?? 0);
      const percentualTotal = percentualBase + bonusCanal;
      const valor = (valorBaseNumerico * percentualTotal) / 100;

      if (valor <= 0) return null;

      return {
        campanha: campanha.name,
        percentual: percentualTotal,
        valor,
      };
    })
    .filter(Boolean);

  const carimbosPrevistos = campanhasElegiveisCanal
    .filter((campanha) => campanha.campaign_type === "loyalty_stamp")
    .map((campanha) => {
      const params = campanha.params || {};
      const valorPorCarimbo = Number(params.min_purchase_value || 0);

      if (valorPorCarimbo <= 0) return null;

      const quantidade = Math.floor(valorBaseNumerico / valorPorCarimbo);
      if (quantidade <= 0) return null;

      return {
        campanha: campanha.name,
        quantidade,
      };
    })
    .filter(Boolean);

  const recompraPrevista = campanhasElegiveisCanal
    .filter((campanha) => campanha.campaign_type === "quick_repurchase")
    .map((campanha) => {
      const params = campanha.params || {};
      const minPurchase = Number(params.min_purchase_value || 0);
      const couponType = String(params.coupon_type || "percent");
      const couponValue = Number(params.coupon_value || 0);

      if (couponValue <= 0 || valorBaseNumerico < minPurchase) return null;

      return {
        campanha: campanha.name,
        tipo: couponType,
        valor: couponValue,
      };
    })
    .filter(Boolean);

  return {
    cashbackPrevisto,
    carimbosPrevistos,
    recompraPrevista,
  };
}
