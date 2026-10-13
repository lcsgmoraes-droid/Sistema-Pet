const MENSAGEM_PADRAO = "Não foi possível concluir a devolução.";

function chave(valor) {
  return typeof valor === "string"
    ? valor
        .trim()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
    : "";
}

function mensagensDoErro(valor, vistos = new Set(), profundidade = 0) {
  if (typeof valor === "string") return valor.trim() ? [valor.trim()] : [];
  if (!valor || typeof valor !== "object" || vistos.has(valor) || profundidade > 6) return [];
  vistos.add(valor);
  if (Array.isArray(valor)) {
    return valor.flatMap((item) => mensagensDoErro(item, vistos, profundidade + 1));
  }
  for (const campo of ["detail", "mensagem", "message", "msg", "errors", "error"]) {
    const mensagens = mensagensDoErro(valor[campo], vistos, profundidade + 1);
    if (mensagens.length) return mensagens;
  }
  return [];
}

function codigoDoErro(valor, vistos = new Set()) {
  if (!valor || typeof valor !== "object" || vistos.has(valor)) return "";
  vistos.add(valor);
  const codigo = valor.codigo || valor.code;
  if (typeof codigo === "string" && !codigo.startsWith("ERR_")) return chave(codigo);
  for (const campo of ["detail", "errors", "error"]) {
    const itens = Array.isArray(valor[campo]) ? valor[campo] : [valor[campo]];
    for (const item of itens) {
      const encontrado = codigoDoErro(item, vistos);
      if (encontrado) return encontrado;
    }
  }
  return "";
}

function possuiCampoValidacao(valor, campo) {
  const itens = Array.isArray(valor) ? valor : Array.isArray(valor?.detail) ? valor.detail : [];
  return itens.some((item) => Array.isArray(item?.loc) && item.loc.includes(campo));
}

function clienteId(venda) {
  const id = venda?.cliente_id || venda?.cliente?.id;
  return /^\d+$/.test(String(id || "")) ? String(id) : null;
}

export function possuiPagamentoBeneficio(venda) {
  return (
    Array.isArray(venda?.pagamentos) &&
    venda.pagamentos.some((pagamento) => {
      if (["recusado", "estornado", "cancelado", "cancelada"].includes(chave(pagamento?.status))) {
        return false;
      }
      const forma = chave(pagamento?.forma_pagamento).replace(/[ -]+/g, "_");
      return ["cashback", "credito_cliente"].includes(forma) && Number(pagamento.valor) > 0;
    })
  );
}

export function criarRecuperacaoDevolucao(erro, { venda, passo = 2 } = {}) {
  if (!erro) return null;
  const payload = erro?.response?.data ?? erro;
  const mensagens = [...new Set(mensagensDoErro(payload))].slice(0, 4);
  const texto = mensagens.join(" ");
  const normalizado = chave(texto);
  const codigo = codigoDoErro(payload);
  const status = Number(erro?.response?.status || erro?.status);
  const idCliente = clienteId(venda);
  const acao = (id, label) => ({ id, label });
  const link = (id, label, href) => ({ id, label, href });
  const atualizar = acao("atualizar_saldos", "Atualizar venda e saldos");
  const itens = acao("foco_itens", "Revisar itens e quantidades");
  const codigoCliente = venda?.cliente?.codigo || venda?.cliente_codigo;
  const gestor = link(
    "abrir_gestor",
    "Abrir carimbos e extrato da cliente",
    `/campanhas?aba=gestor${
      codigoCliente ? `&cliente_codigo=${encodeURIComponent(codigoCliente)}` : ""
    }`,
  );
  const financeiro = link(
    "abrir_financeiro",
    "Abrir contas a receber",
    `/financeiro/contas-receber?filtro=em_aberto${
      idCliente ? `&cliente_id=${encodeURIComponent(idCliente)}` : ""
    }`,
  );
  const extrato = link(
    "abrir_extrato",
    "Consultar histórico financeiro",
    idCliente ? `/clientes/${encodeURIComponent(idCliente)}/financeiro` : "/financeiro/vendas",
  );
  const resultado = (orientacao, acoes, mensagem = texto || MENSAGEM_PADRAO) => ({
    codigo: codigo.toUpperCase() || null,
    mensagem,
    orientacao,
    acoes,
  });
  const temCodigo = (...codigos) =>
    codigos.some(
      (valor) => codigo.replace(/^devolucao_/, "") === chave(valor).replace(/^devolucao_/, ""),
    );

  if (temCodigo("CONFIRMACAO_PENDENTE")) {
    return resultado(
      "A confirmação anterior pode ter sido registrada. Confira a devolução com os mesmos itens, valores e motivo originalmente confirmados antes de iniciar outra. Isso evita uma devolução duplicada.",
      [acao("tentar_novamente", "Conferir devolução anterior")],
    );
  }
  if (temCodigo("CARREGAR_VENDAS")) {
    return resultado(
      "Confira a conexão e carregue a lista novamente. Os filtros de busca permanecem preenchidos.",
      [acao("carregar_vendas", "Carregar vendas novamente")],
    );
  }
  if (temCodigo("CARREGAR_VENDA")) {
    return resultado(
      "Carregue os detalhes da venda novamente para conferir os itens e o saldo disponível.",
      [acao("carregar_venda", "Carregar venda novamente")],
    );
  }

  if (
    temCodigo(
      "DEVOLUCAO_PAGAMENTO_BENEFICIO",
      "PAGAMENTO_BENEFICIO",
      "DEVOLUCAO_BENEFICIO_ORIGEM",
      "BENEFICIO_ORIGEM_OBRIGATORIA",
    ) ||
    /venda foi paga com cashback|concilie a devolucao na forma original/.test(normalizado)
  ) {
    return resultado(
      "Devolva cashback ao saldo de cashback e crédito ao saldo de crédito do cliente. O restante segue a opção dinheiro ou crédito. Revise a prévia antes de confirmar.",
      [acao("devolver_na_origem", "Devolver aos saldos originais")],
    );
  }
  if (temCodigo("DEVOLUCAO_ORIGEM_INCONSISTENTE")) {
    const orientacao = payload?.detail?.acao || payload?.acao;
    if (orientacao === "abrir_beneficios") {
      return resultado(
        "Confira o histórico de cashback e crédito com o responsável antes de devolver. Após conciliar a origem dos valores, volte aqui e atualize a venda.",
        [gestor, extrato, atualizar],
      );
    }
    return resultado(
      "Confira os pagamentos e o cliente vinculado a esta venda com o responsável pelo financeiro. Após conciliar a origem dos valores, volte aqui e atualize a venda.",
      [extrato, atualizar],
    );
  }
  if (
    temCodigo("CAIXA_FECHADO", "CAIXA_OBRIGATORIO", "CAIXA_INDISPONIVEL") ||
    /caixa.*(obrigatorio|nao.*aberto|fechado|indisponivel)|nenhum caixa aberto/.test(normalizado)
  ) {
    return resultado(
      "Abra o caixa nesta tela para devolver em dinheiro. Depois, confirme a devolução novamente.",
      [
        acao("abrir_caixa", "Abrir caixa"),
        ...(idCliente ? [acao("usar_credito", "Devolver o restante em crédito")] : []),
      ],
    );
  }
  if (
    temCodigo("CLIENTE_OBRIGATORIO", "CREDITO_SEM_CLIENTE") ||
    /sem cliente cadastrado|cliente.*(obrigatorio|necessario)|nao possui cliente vinculado/.test(
      normalizado,
    )
  ) {
    return resultado(
      "Esta venda não tem cliente vinculado para receber crédito. Escolha dinheiro para continuar e confira se o caixa está aberto.",
      [acao("usar_dinheiro", "Devolver em dinheiro")],
    );
  }
  if (
    temCodigo("MOTIVO_OBRIGATORIO") ||
    /motivo.*obrigatorio|informe o motivo/.test(normalizado) ||
    possuiCampoValidacao(payload, "motivo")
  ) {
    return resultado("Preencha o motivo da devolução para continuar.", [
      acao("editar_motivo", "Preencher motivo"),
    ]);
  }
  if (
    temCodigo("CARIMBOS_HISTORICO", "FIDELIDADE_HISTORICO", "CASHBACK_SALDO_INSUFICIENTE") ||
    /carimbos antigos|historico do cartao fidelidade|carimbos.*(bloque|concil)|cashback.*(insuficiente|concili)|saldo.*cashback/.test(
      normalizado,
    )
  ) {
    return resultado(
      "Confira o histórico e ajuste a pendência no gestor de campanhas. Depois, volte a esta tela e atualize os saldos. Os itens e o motivo permanecem preenchidos.",
      [gestor, atualizar],
    );
  }
  if (
    temCodigo("RECEBIVEL_ABERTO", "RECEBIVEIS_EM_ABERTO", "CONCILIACAO_FINANCEIRA") ||
    /recebivel em aberto|concilie o valor recebido|recebiveis em aberto/.test(normalizado)
  ) {
    return resultado(
      "Confira os recebimentos desta venda no financeiro e concilie o valor recebido. Ao terminar, volte aqui e atualize os saldos.",
      [financeiro, atualizar],
    );
  }
  if (
    temCodigo(
      "ESTOQUE_CONCILIACAO",
      "PRODUTO_INDISPONIVEL",
      "KIT_VIRTUAL",
      "LOTES_NAO_RASTREAVEIS",
    ) ||
    /estoque.*(manual|rastreavel)|produto original indisponivel|produto nao controla estoque|kit virtual|lotes originais/.test(
      normalizado,
    )
  ) {
    return resultado(
      "Confira o produto e as movimentações de estoque antes de registrar a devolução. Corrija a pendência com o responsável pelo estoque e depois atualize esta venda.",
      [link("abrir_produtos", "Abrir produtos e estoque", "/produtos"), atualizar],
    );
  }
  if (
    temCodigo("HISTORICO_NAO_RASTREAVEL", "DEVOLUCAO_HISTORICO") ||
    /devolucao anterior sem|valor acumulado.*excede|subtotal original|sem base para ratear/.test(
      normalizado,
    )
  ) {
    return resultado(
      "Confira as devoluções e os valores já registrados no histórico financeiro. Após conciliar a pendência, volte aqui e atualize a venda.",
      [extrato, atualizar],
    );
  }
  if (temCodigo("PREVIA_ALTERADA") || /valor da devolucao mudou/.test(normalizado)) {
    return resultado(
      "O valor mudou desde a última prévia. Confira a nova prévia e confirme novamente. Esta tentativa não registrou a devolução.",
      [acao("tentar_novamente", "Revisar nova prévia")],
    );
  }
  if (
    temCodigo("SALDO_INSUFICIENTE", "SALDO_DEVOLUCAO_ALTERADO") ||
    /saldo.*(devolvivel|itens|devolucao)|quantidade.*(excede|fora do saldo)|nao possui saldo/.test(
      normalizado,
    )
  ) {
    return resultado(
      "Atualize a venda para conferir o saldo disponível e revise as quantidades. O motivo e a seleção serão preservados dentro do saldo atual.",
      [atualizar, itens],
    );
  }
  if (
    temCodigo("ITENS_INVALIDOS", "QUANTIDADE_INVALIDA") ||
    /selecione.*item|item.*(invalido|nao encontrado)|quantidade.*invalida|quantidades devem ser maiores que zero|kit inteiro|valor positivo|valor numerico invalido/.test(
      normalizado,
    ) ||
    possuiCampoValidacao(payload, "itens")
  ) {
    return resultado(
      "Selecione os itens e confira as quantidades disponíveis. Para um KIT físico, devolva o KIT inteiro.",
      [itens],
    );
  }
  if (status === 401 || status === 403 || temCodigo("SEM_PERMISSAO")) {
    return resultado(
      "Peça ao responsável para liberar o acesso a devoluções e confirme que sua sessão está ativa. Depois, atualize a venda.",
      [passo === 1 ? acao("carregar_vendas", "Atualizar lista de vendas") : atualizar],
      "Seu acesso precisa ser conferido para continuar a devolução.",
    );
  }
  if (
    temCodigo("VENDA_STATUS_INVALIDO", "VENDA_NAO_ENCONTRADA") ||
    /venda nao encontrada|situacao que permita devolucao/.test(normalizado)
  ) {
    return resultado(
      "Atualize a venda para conferir a situação atual. Consulte o histórico financeiro se ela já foi cancelada ou devolvida.",
      [passo === 1 ? acao("carregar_vendas", "Atualizar lista de vendas") : atualizar, extrato],
    );
  }
  const falhaComunicacao =
    (erro?.isAxiosError && !erro.response) ||
    ["ERR_NETWORK", "ECONNABORTED", "ETIMEDOUT"].includes(erro?.code) ||
    /network error|failed to fetch|timeout|erro ao processar devolucao/.test(normalizado) ||
    status >= 500;
  return resultado(
    falhaComunicacao
      ? "Confira a conexão e tente novamente. Se a confirmação chegou ao sistema, a mesma operação será conferida para evitar uma devolução duplicada."
      : "Sua seleção e o motivo continuam nesta tela. Atualize a venda para conferir os dados e tente confirmar novamente.",
    passo === 1
      ? [acao("carregar_vendas", "Tentar carregar vendas novamente")]
      : venda
        ? [...(falhaComunicacao ? [] : [atualizar]), acao("tentar_novamente", "Tentar novamente")]
        : [acao("carregar_venda", "Carregar venda novamente")],
    falhaComunicacao
      ? "Não foi possível receber a confirmação da devolução."
      : texto || MENSAGEM_PADRAO,
  );
}
