import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../scripts/helpers/reactControllerHarness.mjs";

const alertaPix = (extra = {}) => ({
  id: "pix-42",
  tipo: "pix_nao_identificado",
  titulo: "Pix não identificado da venda 202610220001",
  pagamento_id: 42,
  assinatura: "a".repeat(64),
  registro_id: 17,
  caixa_id: 16,
  numero_caixa: 16,
  caixa_status: "fechado",
  venda_id: 12,
  numero_venda: "202610220001",
  valor: 50,
  operador: "Ana",
  data: "2026-10-01T10:00:00-03:00",
  identificacao_pix: {
    estado: "nao_identificado",
    registro_id: 17,
    justificativa: "Não localizado no extrato.",
    usuario_nome: "Ana",
    data: "2026-10-01T10:00:00-03:00",
    historico: [],
  },
  ...extra,
});
const resposta = (itens = [alertaPix()]) => ({
  itens,
  total: itens.length,
  operadores: [{ id: 1, nome: "Ana" }],
  resumo: {
    venda_justificada: 0,
    diferenca_abertura: 0,
    diferenca_fechamento: 0,
    pix_nao_identificado: itens.length,
  },
});
function adiar() {
  let resolve, reject;
  const promise = new Promise((sim, nao) => {
    resolve = sim;
    reject = nao;
  });
  return { promise, resolve, reject };
}
function preparar() {
  const leituras = [],
    gravacoes = [],
    abas = [];
  const api = {
    get(url, config) {
      const p = adiar();
      leituras.push({ url, config, ...p });
      return p.promise;
    },
    post(url, dados) {
      const p = adiar();
      gravacoes.push({ url, dados, ...p });
      return p.promise;
    },
  };
  const mocks = new Map([
    ["../api", { __esModule: true, default: api }],
    [
      "lucide-react",
      {
        AlertTriangle: "AlertTriangle",
        ExternalLink: "ExternalLink",
        RefreshCw: "RefreshCw",
        Receipt: "Receipt",
        Wallet: "Wallet",
      },
    ],
  ]);
  for (const nome of ["BotaoInteracao", "CartaoIndicador", "InputData", "InputCombobox"]) {
    mocks.set(`../components/v2/${nome}/${nome}`, { __esModule: true, default: nome });
  }
  for (const nome of ["IdentificacaoPixItem", "ModalAuditoriaCaixa"]) {
    mocks.set(`../components/caixa/${nome}`, { __esModule: true, default: nome });
  }
  const h = createControllerHarness(
    fileURLToPath(new URL("./AlertasGestor.jsx", import.meta.url)),
    {
      props: {},
      mocks,
      globals: { window: { open: (...args) => abas.push(args) } },
    },
  );
  const encontrar = (tipo) => elements(h.tree).find((el) => el.type === tipo);
  const botao = (texto) =>
    elements(h.tree).find((el) => el.type === "BotaoInteracao" && elementText(el).includes(texto));
  return { h, leituras, gravacoes, abas, encontrar, botao };
}
async function iniciar(c, dados = resposta()) {
  c.leituras[0].resolve({ data: dados });
  await c.h.settle();
  return c.encontrar("IdentificacaoPixItem").props.item;
}

test("Pix pendente fora do periodo continua visivel e pode ser resolvido depois do fechamento", async () => {
  const c = preparar();
  const item = await iniciar(c);
  assert.match(elementText(c.h.tree), /mesmo fora do período selecionado/);
  assert.equal(c.encontrar("IdentificacaoPixItem").props.bloqueado, false);
  const resultado = c
    .encontrar("IdentificacaoPixItem")
    .props.onSalvar(item, "identificado", "  Banco confirmou o crédito.  ");
  await c.h.settle();
  assert.equal(c.gravacoes[0].url, "/alertas-gestor/pix/42/identificacao");
  assert.deepEqual(c.gravacoes[0].dados, {
    pagamento_id: 42,
    assinatura: "a".repeat(64),
    registro_id: 17,
    estado: "identificado",
    justificativa: "Banco confirmou o crédito.",
  });
  assert.equal(
    c.encontrar("IdentificacaoPixItem").props.item.identificacao_pix.estado,
    "nao_identificado",
  );
  c.gravacoes[0].resolve({ data: { success: true } });
  await c.h.settle();
  assert.equal(c.leituras.length, 2);
  c.leituras[1].resolve({ data: resposta([]) });
  assert.equal(await resultado, true);
  await c.h.settle();
  assert.equal(c.encontrar("IdentificacaoPixItem"), undefined);
  assert.match(elementText(c.h.tree), /Nenhum alerta neste filtro/);
  assert.equal(c.gravacoes.length, 1);
});

test("sem motivo, mesmo estado e duplo clique nao gravam; falha nao remove formulario", async () => {
  const c = preparar();
  const item = await iniciar(c);
  const salvar = c.encontrar("IdentificacaoPixItem").props.onSalvar;
  assert.equal(await salvar(item, "identificado", " "), false);
  assert.equal(await salvar(item, "nao_identificado", "Mesmo estado"), false);
  assert.equal(c.gravacoes.length, 0);
  const resultado = salvar(item, "identificado", "Extrato conferido");
  assert.equal(await salvar(item, "identificado", "Repetir"), false);
  c.gravacoes[0].reject({
    response: { status: 403, data: { detail: "Sem permissão para resolver." } },
  });
  await c.h.settle();
  c.leituras[1].resolve({ data: resposta() });
  assert.equal(await resultado, false);
  await c.h.settle();
  assert.match(elementText(c.h.tree), /Sem permissão para resolver/);
  assert.ok(
    c.encontrar("IdentificacaoPixItem"),
    "Erro de gravacao nao desmonta o componente e seu motivo",
  );
  assert.equal(c.encontrar("IdentificacaoPixItem").props.salvando, false);
  assert.equal(c.gravacoes.length, 1);
});

test("conflito recarrega metadados sem repetir POST; assinatura anterior fica impedida", async () => {
  const c = preparar();
  const item = await iniciar(c);
  const resultado = c
    .encontrar("IdentificacaoPixItem")
    .props.onSalvar(item, "identificado", "Novo comprovante");
  c.gravacoes[0].reject({ response: { status: 409 } });
  await c.h.settle();
  const novo = alertaPix({
    assinatura: "b".repeat(64),
    registro_id: 18,
    identificacao_pix: { ...item.identificacao_pix, registro_id: 18 },
  });
  c.leituras[1].resolve({ data: resposta([novo]) });
  assert.equal(await resultado, false);
  await c.h.settle();
  assert.equal(c.encontrar("IdentificacaoPixItem").props.item.assinatura, "b".repeat(64));
  assert.match(elementText(c.h.tree), /outra pessoa/);
  assert.equal(
    await c
      .encontrar("IdentificacaoPixItem")
      .props.onSalvar(item, "identificado", "Tentativa antiga"),
    false,
  );
  assert.equal(c.gravacoes.length, 1);
});

test("POST salvo seguido de falha na leitura conserva alerta e bloqueia nova gravacao ate atualizar", async () => {
  const c = preparar();
  const item = await iniciar(c);
  const resultado = c
    .encontrar("IdentificacaoPixItem")
    .props.onSalvar(item, "identificado", "Crédito no banco");
  c.gravacoes[0].resolve({ data: { success: true } });
  await c.h.settle();
  c.leituras[1].reject(new Error("offline"));
  assert.equal(await resultado, false);
  await c.h.settle();
  assert.ok(c.encontrar("IdentificacaoPixItem"));
  assert.equal(c.encontrar("IdentificacaoPixItem").props.bloqueado, true);
  assert.match(elementText(c.h.tree), /Identificação salva/);
  await c.h.act(() => c.botao("Atualizar").props.onClick());
  c.leituras[2].resolve({ data: resposta([]) });
  await c.h.settle();
  assert.equal(c.encontrar("IdentificacaoPixItem"), undefined);
});

test("alerta mostra referencia do caixa e consulta venda sem acessar auditoria pessoal; filtro Pix correto", async () => {
  const c = preparar();
  await iniciar(c);
  assert.equal(c.botao("Auditar caixa"), undefined);
  await c.h.act(() => c.botao("Abrir venda").props.onClick());
  assert.deepEqual(c.abas, [["/pdv?venda=12", "_blank", "noopener,noreferrer"]]);
  assert.equal(c.gravacoes.length, 0);
  const filtro = elements(c.h.tree).find(
    (el) => el.type === "InputCombobox" && el.props.id === "alertas-tipo",
  );
  assert.ok(filtro.props.opcoes.some((opcao) => opcao.value === "pix_nao_identificado"));
  await c.h.act(() => filtro.props.onChange("pix_nao_identificado"));
  assert.equal(c.leituras.at(-1).config.params.tipo, "pix_nao_identificado");
});

test("resolver ultimo alerta da pagina 2 volta a pagina valida e rele sem mostrar lista vazia falsa", async () => {
  const c = preparar();
  await iniciar(c, { ...resposta(), total: 31 });
  await c.h.act(() => c.botao("Próxima").props.onClick());
  assert.equal(c.leituras[1].config.params.pagina, 2);
  c.leituras[1].resolve({ data: { ...resposta(), total: 31 } });
  await c.h.settle();
  const pix = c.encontrar("IdentificacaoPixItem").props;
  const resultado = pix.onSalvar(pix.item, "identificado", "Comprovante confirmado.");
  c.gravacoes[0].resolve({ data: { success: true } });
  await c.h.settle();
  assert.equal(c.leituras[2].config.params.pagina, 2);
  c.leituras[2].resolve({ data: { ...resposta([]), total: 30 } });
  assert.equal(await resultado, true);
  await c.h.settle();
  assert.equal(c.leituras[3].config.params.pagina, 1);
  assert.doesNotMatch(elementText(c.h.tree), /Nenhum alerta neste filtro/);
  assert.match(elementText(c.h.tree), /Carregando alertas/);
  const pendente = alertaPix({ id: "pix-43", pagamento_id: 43 });
  c.leituras[3].resolve({ data: { ...resposta([pendente]), total: 30 } });
  await c.h.settle();
  assert.equal(c.botao("Anterior").props.disabled, true);
  assert.equal(c.botao("Próxima").props.disabled, true);
  assert.equal(c.encontrar("IdentificacaoPixItem").props.item.id, 43);
  assert.equal(c.encontrar("IdentificacaoPixItem").props.salvando, false);
  assert.equal(c.gravacoes.length, 1);
});
