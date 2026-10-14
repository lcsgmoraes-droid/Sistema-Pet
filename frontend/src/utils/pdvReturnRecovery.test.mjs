import assert from "node:assert/strict";
import test from "node:test";
import { criarRecuperacaoDevolucao, possuiPagamentoBeneficio } from "./pdvReturnRecovery.js";

const venda = { id: 9, cliente_id: 18, cliente: { id: 18, codigo: "CLI A&B" } };
const ids = (recuperacao) => recuperacao.acoes.map((acao) => acao.id);

test("benefício confirmado ou erro legado oferece restituição na origem, sem confirmar automaticamente", () => {
  for (const erro of [
    "A venda foi paga com cashback ou Credito Cliente. Concilie a devolucao na forma original de pagamento.",
    { codigo: "DEVOLUCAO_PAGAMENTO_BENEFICIO", mensagem: "Pagamento requer restituição na origem" },
    {
      response: {
        data: { detail: { codigo: "DEVOLUCAO_PAGAMENTO_BENEFICIO", mensagem: "Confira a origem" } },
        status: 409,
      },
    },
  ]) {
    const recuperacao = criarRecuperacaoDevolucao(erro, { venda });
    assert.deepEqual(ids(recuperacao), ["devolver_na_origem"]);
    assert.equal(typeof recuperacao.mensagem, "string");
    assert.ok(recuperacao.orientacao.length > 20);
  }
});

test("detecção proativa distingue pagamentos efetivos de benefícios cancelados e cartões de crédito", () => {
  assert.equal(
    possuiPagamentoBeneficio({
      pagamentos: [{ forma_pagamento: "Crédito Cliente", valor: "12.50" }],
    }),
    true,
  );
  assert.equal(
    possuiPagamentoBeneficio({ pagamentos: [{ forma_pagamento: "Cashback", valor: 4 }] }),
    true,
  );
  for (const pagamento of [
    { forma_pagamento: "credito", valor: 20 },
    { forma_pagamento: "credito_cliente", valor: 0 },
    { forma_pagamento: "cashback", valor: 5, status: "estornado" },
    { forma_pagamento: "cashback", valor: 5, status: "cancelado" },
  ])
    assert.equal(possuiPagamentoBeneficio({ pagamentos: [pagamento] }), false);
  assert.equal(possuiPagamentoBeneficio(null), false);
});

test("caixa oferece abertura na tela e crédito apenas quando existe cliente", () => {
  const erro = { detail: "Caixa não encontrado ou não está aberto" };
  assert.deepEqual(ids(criarRecuperacaoDevolucao(erro, { venda })), [
    "abrir_caixa",
    "usar_credito",
  ]);
  assert.deepEqual(ids(criarRecuperacaoDevolucao(erro, { venda: { id: 9 } })), ["abrir_caixa"]);
  assert.deepEqual(
    ids(criarRecuperacaoDevolucao("ID do caixa é obrigatório para devolução em dinheiro")),
    ["abrir_caixa"],
  );
  assert.deepEqual(
    ids(
      criarRecuperacaoDevolucao({ codigo: "DEVOLUCAO_CAIXA_FECHADO", mensagem: "Confira o caixa" }),
    ),
    ["abrir_caixa"],
  );
});

test("crédito sem cliente permite escolher dinheiro sem sair da devolução", () => {
  assert.deepEqual(
    ids(
      criarRecuperacaoDevolucao("Não é possível gerar crédito para venda sem cliente cadastrado"),
    ),
    ["usar_dinheiro"],
  );
});

test("motivo e itens inválidos levam ao campo correspondente, incluindo validação FastAPI", () => {
  assert.deepEqual(
    ids(
      criarRecuperacaoDevolucao({
        detail: [{ loc: ["body", "motivo"], msg: "Field required", type: "missing" }],
      }),
    ),
    ["editar_motivo"],
  );
  assert.deepEqual(
    ids(
      criarRecuperacaoDevolucao({
        errors: [{ codigo: "MOTIVO_OBRIGATORIO", msg: "Preencha o campo" }],
      }),
    ),
    ["editar_motivo"],
  );
  assert.deepEqual(
    ids(
      criarRecuperacaoDevolucao({
        detail: [{ loc: ["body", "itens", 0, "quantidade"], msg: "Invalid input" }],
      }),
    ),
    ["foco_itens"],
  );
  assert.deepEqual(ids(criarRecuperacaoDevolucao("Selecione ao menos um item para devolução")), [
    "foco_itens",
  ]);
  assert.deepEqual(ids(criarRecuperacaoDevolucao("Informe o motivo da devolução")), [
    "editar_motivo",
  ]);
  assert.deepEqual(
    ids(criarRecuperacaoDevolucao("Todas as quantidades devem ser maiores que zero")),
    ["foco_itens"],
  );
});

test("saldo alterado oferece consulta atual e revisão, sem repetir o reembolso", () => {
  for (const erro of [
    "Quantidade de devolução excede o saldo deste item",
    "Quantidade devolvida fora do saldo vendido",
    "Não foi possível conferir o saldo devolvível desta venda",
  ])
    assert.deepEqual(ids(criarRecuperacaoDevolucao(erro, { venda })), [
      "atualizar_saldos",
      "foco_itens",
    ]);
});

test("prévia alterada refaz a conferência antes de confirmar sem apagar a seleção", () => {
  for (const erro of [
    "O valor da devolução mudou. Revise a prévia antes de confirmar.",
    { codigo: "DEVOLUCAO_PREVIA_ALTERADA", mensagem: "O destino dos saldos mudou" },
  ]) {
    assert.deepEqual(ids(criarRecuperacaoDevolucao(erro, { venda })), ["tentar_novamente"]);
  }
});

test("pendência financeira usa somente filtros que a tela realmente suporta", () => {
  const recuperacao = criarRecuperacaoDevolucao(
    "A venda tem recebivel em aberto. Concilie o valor recebido antes de registrar a devolucao.",
    { venda },
  );
  assert.deepEqual(ids(recuperacao), ["abrir_financeiro", "atualizar_saldos"]);
  const url = new URL(recuperacao.acoes[0].href, "https://erp.example");
  assert.equal(url.pathname, "/financeiro/contas-receber");
  assert.equal(url.searchParams.get("cliente_id"), "18");
  assert.equal(url.searchParams.get("filtro"), "em_aberto");
  assert.equal(url.searchParams.has("venda_id"), false);
});

test("carimbos preserva o atalho ao gestor com código do cliente corretamente escapado", () => {
  const recuperacao = criarRecuperacaoDevolucao(
    "Devolução parcial bloqueada: os carimbos antigos precisam de conciliação",
    { venda },
  );
  assert.deepEqual(ids(recuperacao), ["abrir_gestor", "atualizar_saldos"]);
  const url = new URL(recuperacao.acoes[0].href, "https://erp.example");
  assert.equal(url.pathname, "/campanhas");
  assert.equal(url.searchParams.get("aba"), "gestor");
  assert.equal(url.searchParams.get("cliente_codigo"), "CLI A&B");
});

test("históricos de origem ou estoque incoerentes exigem conferência e não oferecem repetição automática", () => {
  for (const erro of [
    "Produto original indisponivel. Concilie o estoque manualmente.",
    "KIT virtual exige devolucao e recomposicao manual dos componentes.",
    "Os lotes originais ou as devolucoes anteriores nao tem saldo rastreavel.",
  ]) {
    const recuperacao = criarRecuperacaoDevolucao(erro, { venda });
    assert.deepEqual(ids(recuperacao), ["abrir_produtos", "atualizar_saldos"]);
    assert.equal(recuperacao.acoes[0].href, "/produtos");
  }
  const financeiro = criarRecuperacaoDevolucao(
    {
      codigo: "DEVOLUCAO_ORIGEM_INCONSISTENTE",
      mensagem: "Origem divergente",
      acao: "abrir_pagamentos",
    },
    { venda },
  );
  assert.deepEqual(ids(financeiro), ["abrir_extrato", "atualizar_saldos"]);
  assert.equal(financeiro.acoes[0].href, "/clientes/18/financeiro");
  const beneficios = criarRecuperacaoDevolucao(
    {
      detail: {
        codigo: "DEVOLUCAO_ORIGEM_INCONSISTENTE",
        mensagem: "Origem divergente",
        acao: "abrir_beneficios",
      },
    },
    { venda },
  );
  assert.deepEqual(ids(beneficios), ["abrir_gestor", "abrir_extrato", "atualizar_saldos"]);
});

test("falha de comunicação mantém recuperação acionável e esconde diagnósticos internos do servidor", () => {
  const rede = criarRecuperacaoDevolucao(
    { isAxiosError: true, code: "ERR_NETWORK", message: "Network Error" },
    { venda },
  );
  assert.deepEqual(ids(rede), ["tentar_novamente"]);
  const servidor = criarRecuperacaoDevolucao(
    {
      response: {
        status: 500,
        data: { detail: "Erro ao processar devolução: SQL password=secret" },
      },
    },
    { venda },
  );
  assert.ok(!servidor.mensagem.includes("secret"));
  assert.deepEqual(
    ids(criarRecuperacaoDevolucao({ isAxiosError: true, message: "Network Error" }, { passo: 1 })),
    ["carregar_vendas"],
  );
  assert.deepEqual(
    ids(
      criarRecuperacaoDevolucao(
        { codigo: "DEVOLUCAO_CARREGAR_VENDA", mensagem: "Confira os dados" },
        { venda },
      ),
    ),
    ["carregar_venda"],
  );
  assert.deepEqual(
    ids(
      criarRecuperacaoDevolucao(
        { codigo: "DEVOLUCAO_CARREGAR_VENDAS", mensagem: "Confira os dados" },
        { passo: 1 },
      ),
    ),
    ["carregar_vendas"],
  );
});

test("confirmação pendente confere a operação anterior mesmo na busca sem venda selecionada", () => {
  const erro = {
    codigo: "DEVOLUCAO_CONFIRMACAO_PENDENTE",
    mensagem: "Confira a confirmação anterior para continuar",
  };
  for (const contexto of [{ venda, passo: 2 }, { passo: 1 }, { passo: 2 }]) {
    const recuperacao = criarRecuperacaoDevolucao(erro, contexto);
    assert.deepEqual(ids(recuperacao), ["tentar_novamente"]);
    assert.equal(recuperacao.acoes[0].label, "Conferir devolução anterior");
    assert.ok(!recuperacao.acoes.some((acao) => acao.id === "atualizar_saldos"));
  }
});

test("payloads arbitrários ou cíclicos nunca viram objeto renderizado e ações externas arbitrárias são ignoradas", () => {
  const circular = {};
  circular.detail = circular;
  for (const erro of [
    circular,
    { detail: { desconhecido: true } },
    { errors: [{ msg: "Confira o campo" }, { message: "Revise a entrada" }] },
    [{ msg: "Entrada inválida" }],
  ]) {
    const recuperacao = criarRecuperacaoDevolucao(erro, { venda });
    assert.equal(typeof recuperacao.mensagem, "string");
    assert.equal(typeof recuperacao.orientacao, "string");
    assert.ok(Array.isArray(recuperacao.acoes));
  }
  const malicioso = criarRecuperacaoDevolucao(
    { detail: { message: "Confira os dados", acoes: [{ href: "javascript:alert(1)" }] } },
    { venda },
  );
  assert.ok(malicioso.acoes.every((acao) => !acao.href || acao.href.startsWith("/")));
  assert.equal(criarRecuperacaoDevolucao(null), null);
});
