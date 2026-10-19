import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../../scripts/helpers/reactControllerHarness.mjs";
import { MODELO_CASHBACK } from "./cashbackCrmUtils.js";

const componentPath = fileURLToPath(new URL("./useCashbackModelo.js", import.meta.url));
const usuario = { id: 7, tenant: { id: "empresa-a" } };
const chave = (user) =>
  `corepet:cashback-modelo:v1:${user.tenant?.id || user.tenant_id}:${user.id}`;
const preferencia = (personalizado, selecao = "minha") =>
  JSON.stringify({ versao: 1, selecao, personalizado });

function armazenamento(entradas = []) {
  const dados = new Map(entradas);
  const gravacoes = [];
  return {
    dados,
    gravacoes,
    getItem: (key) => dados.get(key) ?? null,
    setItem(key, value) {
      gravacoes.push({ key, value });
      dados.set(key, value);
    },
  };
}

function montar(storage, user = usuario, janela = { localStorage: storage }) {
  return createControllerHarness(componentPath, {
    props: user,
    mocks: new Map(),
    globals: { window: janela },
  });
}

test("começa com o padrão e recupera a mensagem editada ao voltar à tela", async () => {
  const storage = armazenamento();
  const primeiraVisita = montar(storage);
  await primeiraVisita.settle();
  assert.equal(primeiraVisita.tree.tipoModelo, "padrao");
  assert.equal(primeiraVisita.tree.modelo, MODELO_CASHBACK);

  const mensagem = "Oi, {nome}! Seu cashback de {saldo} está te esperando 🐾";
  await primeiraVisita.act(() => primeiraVisita.tree.setModelo(mensagem));
  assert.equal(primeiraVisita.tree.tipoModelo, "minha");
  assert.equal(primeiraVisita.tree.modelo, mensagem);

  const segundaVisita = montar(storage);
  await segundaVisita.settle();
  assert.equal(segundaVisita.tree.tipoModelo, "minha");
  assert.equal(segundaVisita.tree.modelo, mensagem);
  assert.ok(!segundaVisita.tree.erroModelo);
});

test("lembra a última seleção padrão sem perder a mensagem personalizada", async () => {
  const storage = armazenamento();
  const primeiraVisita = montar(storage);
  await primeiraVisita.act(() => primeiraVisita.tree.setModelo("Minha oferta para {nome}"));
  await primeiraVisita.act(() => primeiraVisita.tree.selecionarModelo("padrao"));
  assert.equal(primeiraVisita.tree.modelo, MODELO_CASHBACK);

  const segundaVisita = montar(storage);
  await segundaVisita.settle();
  assert.equal(segundaVisita.tree.tipoModelo, "padrao");
  assert.equal(segundaVisita.tree.modelo, MODELO_CASHBACK);
  await segundaVisita.act(() => segundaVisita.tree.selecionarModelo("minha"));
  assert.equal(segundaVisita.tree.modelo, "Minha oferta para {nome}");
  await segundaVisita.act(() => segundaVisita.tree.selecionarModelo("padrao"));
  await segundaVisita.act(() => segundaVisita.tree.selecionarModelo("minha"));
  assert.equal(segundaVisita.tree.modelo, "Minha oferta para {nome}");
});

test("a primeira mensagem própria começa com a sugestão padrão", async () => {
  const harness = montar(armazenamento());
  await harness.act(() => harness.tree.selecionarModelo("minha"));
  assert.equal(harness.tree.tipoModelo, "minha");
  assert.equal(harness.tree.modelo, MODELO_CASHBACK);
});

test("mantém preferências separadas por usuário e empresa ao trocar a identidade", async () => {
  const outroUsuario = { id: 8, tenant: { id: "empresa-a" } };
  const outraEmpresa = { id: 7, tenant: { id: "empresa-b" } };
  const storage = armazenamento([
    [chave(usuario), preferencia("Mensagem do usuário 7 na empresa A")],
    [chave(outroUsuario), preferencia("Mensagem do usuário 8 na empresa A")],
    [chave(outraEmpresa), preferencia("Mensagem do usuário 7 na empresa B")],
  ]);
  const harness = montar(storage);
  await harness.settle();
  assert.equal(harness.tree.modelo, "Mensagem do usuário 7 na empresa A");

  await harness.update(outroUsuario);
  assert.equal(harness.tree.modelo, "Mensagem do usuário 8 na empresa A");
  await harness.act(() => harness.tree.setModelo("Nova mensagem apenas do usuário 8"));
  await harness.update(outraEmpresa);
  assert.equal(harness.tree.modelo, "Mensagem do usuário 7 na empresa B");
  await harness.update(usuario);
  assert.equal(harness.tree.modelo, "Mensagem do usuário 7 na empresa A");
  assert.equal(
    JSON.parse(storage.dados.get(chave(outroUsuario))).personalizado,
    "Nova mensagem apenas do usuário 8",
  );
  assert.equal(
    JSON.parse(storage.dados.get(chave(outraEmpresa))).personalizado,
    "Mensagem do usuário 7 na empresa B",
  );
});

test("reconhece tenant_id quando a sessão não contém o objeto tenant", async () => {
  const user = { id: "usuario-9", tenant_id: "empresa-c" };
  const storage = armazenamento([[chave(user), preferencia("Mensagem da empresa C")]]);
  const harness = montar(storage, user);
  await harness.settle();
  assert.equal(harness.tree.modelo, "Mensagem da empresa C");
  await harness.act(() => harness.tree.setModelo("Texto atualizado"));
  assert.equal(JSON.parse(storage.dados.get(chave(user))).personalizado, "Texto atualizado");
});

test("não grava mensagens sem usuário ou empresa e carrega a preferência após o login", async () => {
  for (const identidade of [{}, { id: 7 }, { tenant_id: "empresa-a" }]) {
    const storage = armazenamento([[chave(usuario), preferencia("Mensagem já salva")]]);
    const harness = montar(storage, identidade);
    await harness.act(() => harness.tree.setModelo("Texto temporário sem identidade"));
    assert.equal(harness.tree.modelo, "Texto temporário sem identidade");
    assert.equal(storage.gravacoes.length, 0);
    await harness.update(usuario);
    assert.equal(harness.tree.modelo, "Mensagem já salva");
    assert.ok(storage.gravacoes.every((item) => item.key === chave(usuario)));
  }
});

test("conserva o texto em memória e informa quando a gravação é bloqueada", async () => {
  const storage = armazenamento();
  storage.setItem = () => {
    throw new Error("QuotaExceededError");
  };
  const harness = montar(storage);
  await harness.act(() => harness.tree.setModelo("Texto que precisa continuar na tela"));
  assert.equal(harness.tree.tipoModelo, "minha");
  assert.equal(harness.tree.modelo, "Texto que precisa continuar na tela");
  assert.ok(harness.tree.erroModelo);
  await harness.act(() => harness.tree.selecionarModelo("padrao"));
  await harness.act(() => harness.tree.selecionarModelo("minha"));
  assert.equal(harness.tree.modelo, "Texto que precisa continuar na tela");
});

test("a tela continua utilizável quando acessar localStorage falha", async () => {
  const janela = {};
  Object.defineProperty(janela, "localStorage", {
    get() {
      throw new Error("SecurityError");
    },
  });
  const harness = montar(undefined, usuario, janela);
  await harness.settle();
  assert.equal(harness.tree.modelo, MODELO_CASHBACK);
  assert.ok(harness.tree.erroModelo);
  await harness.act(() => harness.tree.setModelo("Texto guardado só em memória"));
  assert.equal(harness.tree.modelo, "Texto guardado só em memória");
  assert.ok(harness.tree.erroModelo);
});

test("ignora preferências corrompidas ou incompatíveis sem impedir o uso da tela", async () => {
  const valoresInvalidos = [
    ["{json incompleto", "padrao"],
    ["null", "padrao"],
    ["[]", "padrao"],
    [preferencia("Texto", "selecao-desconhecida"), "padrao"],
    [JSON.stringify({ versao: 2, selecao: "minha", personalizado: "Outra versão" }), "padrao"],
    [
      JSON.stringify({ versao: 1, selecao: "minha", personalizado: { texto: "Inválido" } }),
      "minha",
    ],
  ];
  for (const [valor, selecao] of valoresInvalidos) {
    const harness = montar(armazenamento([[chave(usuario), valor]]));
    await harness.settle();
    assert.equal(harness.tree.modelo, MODELO_CASHBACK, valor);
    assert.equal(harness.tree.tipoModelo, selecao, valor);
    await harness.act(() => harness.tree.setModelo("Mensagem recuperada"));
    assert.equal(harness.tree.modelo, "Mensagem recuperada");
  }
});

test("preserva uma mensagem própria vazia ao sair, voltar e alternar", async () => {
  const storage = armazenamento();
  const primeiraVisita = montar(storage);
  await primeiraVisita.act(() => primeiraVisita.tree.setModelo(""));
  assert.equal(primeiraVisita.tree.modelo, "");
  const segundaVisita = montar(storage);
  await segundaVisita.settle();
  assert.equal(segundaVisita.tree.tipoModelo, "minha");
  assert.equal(segundaVisita.tree.modelo, "");
  await segundaVisita.act(() => segundaVisita.tree.selecionarModelo("padrao"));
  await segundaVisita.act(() => segundaVisita.tree.selecionarModelo("minha"));
  assert.equal(segundaVisita.tree.modelo, "");
});

test("limita mensagens novas a 2000 caracteres e recupera o texto limitado", async () => {
  const storage = armazenamento();
  const harness = montar(storage);
  await harness.act(() => harness.tree.setModelo("a".repeat(2001)));
  assert.equal(harness.tree.modelo, "a".repeat(2000));
  const segundaVisita = montar(storage);
  await segundaVisita.settle();
  assert.equal(segundaVisita.tree.modelo, "a".repeat(2000));
});

test("recusa um texto armazenado acima do limite e aceita corrigir o modelo", async () => {
  const storage = armazenamento([[chave(usuario), preferencia("a".repeat(2001))]]);
  const harness = montar(storage);
  await harness.settle();
  assert.equal(harness.tree.modelo, MODELO_CASHBACK);
  await harness.act(() => harness.tree.setModelo("Mensagem corrigida"));
  const segundaVisita = montar(storage);
  await segundaVisita.settle();
  assert.equal(segundaVisita.tree.modelo, "Mensagem corrigida");
});
