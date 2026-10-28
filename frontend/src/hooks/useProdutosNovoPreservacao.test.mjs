import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../scripts/helpers/reactControllerHarness.mjs";

const noOp = () => {};
const source = (name) => fileURLToPath(new URL(`./${name}.js`, import.meta.url));

async function setup({
  product = {},
  fiscal = {},
  failFiscal = false,
  isEdicao = true,
  isClone = false,
} = {}) {
  const env = {
    product: {
      id: 7,
      codigo: "DEV-FICTICIO",
      nome: "Produto fictício",
      tipo: "produto",
      tipo_produto: "SIMPLES",
      preco_venda: 100,
      preco_custo: 60,
      estoque_maximo: 0,
      origem: null,
      anunciar_ifood: true,
      ifood_pausado: false,
      ...product,
    },
    fiscal: {
      origem: "produto_legado",
      herdado_da_empresa: false,
      origem_mercadoria: null,
      ncm: null,
      ...fiscal,
    },
    failFiscal,
    failSaveFiscal: false,
  };
  const calls = { fiscal: [], products: [], creates: [], alerts: [], navigation: [] };
  let formData = {};
  const setFormData = (update) => {
    formData = typeof update === "function" ? update(formData) : update;
  };
  const api = {
    get: async (path) => {
      if (path.endsWith("/fiscal")) {
        if (env.failFiscal) throw Error("Fiscal indisponível");
        return { data: { ...env.fiscal } };
      }
      return { data: [] };
    },
    put: async (path, body) => {
      calls.fiscal.push({ path, body });
      if (env.failSaveFiscal) throw Error("Falha ao salvar fiscal");
      return { data: {} };
    },
  };
  const productApi = {
    getProduto: async () => ({ data: { ...env.product } }),
    getCategorias: async () => ({ data: [] }),
    getDepartamentos: async () => ({ data: [] }),
    getMarcas: async () => ({ data: [] }),
    getLotes: async () => ({ data: [] }),
    getFornecedoresProduto: async () => ({ data: [] }),
    previewPrecosVendaProdutosCompostos: async () => ({ data: { sugestoes: [] } }),
    createProduto: async (body) => {
      calls.creates.push(body);
      return { data: { id: 99 } };
    },
    updateProduto: async (id, body) => {
      calls.products.push({ id, body });
      return { data: { id } };
    },
  };
  const mocks = new Map([
    ["../api", { __esModule: true, default: api }],
    ["../api/produtos", productApi],
    ["../utils/debug", { debugLog: noOp }],
  ]);
  const loader = createControllerHarness(source("useProdutosNovoCarregamento"), {
    mocks,
    globals: { console: { error: noOp } },
    props: {
      id: isEdicao ? env.product.id : undefined,
      cloneId: isClone ? env.product.id : undefined,
      isEdicao,
      formData,
      setFormData,
      ...Object.fromEntries(
        [
          "setCategorias",
          "setCategoriasHierarquicas",
          "setMarcas",
          "setDepartamentos",
          "setClientes",
          "setOpcoesLinhas",
          "setOpcoesPortes",
          "setOpcoesFases",
          "setOpcoesTratamentos",
          "setOpcoesSabores",
          "setOpcoesApresentacoes",
          "setLoading",
          "setErroCarregamento",
          "setPredecessorInfo",
          "setSucessorInfo",
          "setImagens",
          "setLotes",
          "setFornecedores",
          "setGranelVinculos",
        ].map((name) => [name, noOp]),
      ),
    },
  });
  await loader.settle();
  await loader.update({ formData });
  const fiscalEditor = createControllerHarness(source("useProdutosNovoTributacao"), {
    mocks,
    props: { setFormData },
  });

  return {
    env,
    calls,
    loader,
    get form() {
      return formData;
    },
    async edit(changes) {
      setFormData((previous) => ({ ...previous, ...changes }));
      await loader.update({ formData });
    },
    async editFiscal(field, value) {
      await fiscalEditor.act(() => fiscalEditor.tree.handleChangeTributacao(field, value));
      await loader.update({ formData });
    },
    async personalizeFiscal() {
      await fiscalEditor.act(() => fiscalEditor.tree.handlePersonalizarFiscal());
      await loader.update({ formData });
    },
    async submit() {
      const submitter = createControllerHarness(source("useProdutosNovoSubmit"), {
        mocks,
        globals: {
          console: { error: noOp },
          alert: (message) => calls.alerts.push(message),
        },
        props: {
          id: env.product.id,
          isEdicao,
          isClone,
          formData,
          salvarFiscal: loader.tree.salvarFiscal,
          setSalvando: noOp,
          navigate: (path) => calls.navigation.push(path),
          produtosOrigemGranel: [],
          granelVinculos: [],
        },
      });
      await submitter.act(() => submitter.tree.handleSubmit({ preventDefault: noOp }));
    },
    async reload() {
      await loader.act(() => loader.tree.carregarProduto());
      await loader.update({ formData });
    },
    async switchProduct(product, fiscal) {
      env.product = { ...env.product, ...product };
      env.fiscal = { ...env.fiscal, ...fiscal };
      await loader.update({ id: env.product.id });
      await loader.update({ formData });
    },
  };
}

test("salvar apenas pausa mantém estoque máximo zero sem materializar origem fiscal nula", async () => {
  const h = await setup();
  assert.equal(h.form.estoque_maximo, 0);
  assert.equal(h.form.tributacao.origem_mercadoria, "0");
  await h.edit({ ifood_pausado: true });
  await h.submit();
  assert.equal(h.calls.products.length, 1);
  assert.equal(h.calls.products[0].body.ifood_pausado, true);
  assert.equal(h.calls.products[0].body.estoque_maximo, 0);
  assert.equal(Object.hasOwn(h.calls.products[0].body, "origem"), false);
  assert.deepEqual(h.calls.fiscal, []);
  assert.equal(h.env.product.origem, null);
  assert.deepEqual(h.calls.navigation, ["/produtos"]);
});

test("salvar outra aba preserva fiscal herdado e não cria personalização", async () => {
  const h = await setup({
    fiscal: { origem: "empresa_legado", herdado_da_empresa: true, ncm: "12345678" },
  });
  await h.edit({ ifood_pausado: true });
  await h.submit();
  assert.equal(h.form.tributacao.herdado_da_empresa, true);
  assert.deepEqual(h.calls.fiscal, []);
  assert.equal(h.calls.products.length, 1);
});

test("fiscal V2 já personalizado e inalterado também não é regravado", async () => {
  const h = await setup({
    fiscal: { origem: "produto_fiscal_v2", ncm: "12345678", origem_mercadoria: "1" },
  });
  await h.edit({ ifood_pausado: true });
  await h.submit();
  assert.deepEqual(h.calls.fiscal, []);
  assert.equal(h.calls.products.length, 1);
});

test("editar tributação de verdade salva fiscal e o produto", async () => {
  const h = await setup();
  await h.editFiscal("origem_mercadoria", "1");
  await h.editFiscal("ncm", "12345678");
  await h.submit();
  assert.equal(h.calls.fiscal.length, 1);
  assert.equal(h.calls.fiscal[0].path, "/produtos/7/fiscal");
  assert.equal(h.calls.fiscal[0].body.origem_mercadoria, "1");
  assert.equal(h.calls.fiscal[0].body.ncm, "12345678");
  assert.equal(h.calls.products.length, 1);
  await h.edit({ ifood_pausado: true });
  await h.submit();
  assert.equal(h.calls.fiscal.length, 1, "o fiscal já salvo não é enviado novamente");
  assert.equal(h.calls.products.length, 2);
});

test("Personalizar fiscal continua salvando valores herdados mesmo sem editar campos", async () => {
  const h = await setup({
    product: { tipo_produto: "KIT" },
    fiscal: { herdado_da_empresa: true, origem_mercadoria: "2", ncm: "12345678" },
  });
  await h.personalizeFiscal();
  await h.submit();
  assert.equal(h.calls.fiscal.length, 1);
  assert.equal(h.calls.fiscal[0].path, "/produtos/7/kit/fiscal");
  assert.equal(h.calls.fiscal[0].body.origem_mercadoria, "2");
  assert.equal(h.calls.fiscal[0].body.ncm, "12345678");
});

test("alterar e desfazer fiscal antes de salvar pausa mantém a origem nula", async () => {
  const h = await setup();
  await h.editFiscal("origem_mercadoria", "1");
  await h.editFiscal("origem_mercadoria", "0");
  await h.edit({ ifood_pausado: true });
  await h.submit();
  assert.deepEqual(h.calls.fiscal, []);
  assert.equal(h.calls.products.length, 1);
});

test("limpar campos fiscais e informar false ou zero continua sendo edição explícita", async () => {
  const h = await setup({
    fiscal: { ncm: "12345678", cest: "1234567", cfop: "5102", icms_st: true, pis_aliquota: 2 },
  });
  await h.editFiscal("ncm", "");
  await h.editFiscal("cest", "");
  await h.editFiscal("cfop", "");
  await h.editFiscal("icms_st", false);
  await h.editFiscal("pis_aliquota", "0");
  await h.submit();
  assert.equal(h.calls.fiscal.length, 1);
  const { body } = h.calls.fiscal[0];
  assert.equal(body.ncm, "");
  assert.equal(body.cest, "");
  assert.equal(body.cfop, "");
  assert.equal(body.icms_st, false);
  assert.equal(body.pis_aliquota, "0");
});

test("estoque máximo nulo, vazio, zero digitado e positivo têm valores distintos no payload", async () => {
  const h = await setup({ product: { estoque_maximo: null } });
  assert.equal(h.form.estoque_maximo, "");
  for (const [input, expected] of [
    ["", null],
    [null, null],
    ["0", 0],
    ["28", 28],
  ]) {
    await h.edit({ estoque_maximo: input });
    await h.submit();
    assert.equal(h.calls.products.at(-1).body.estoque_maximo, expected);
  }
  assert.deepEqual(h.calls.fiscal, []);
});

test("falha de carga fiscal não permite salvar defaults e pode ser recuperada sem perder pausa", async () => {
  const h = await setup({ failFiscal: true });
  await h.edit({ ifood_pausado: true });
  await h.submit();
  assert.deepEqual(h.calls.products, []);
  assert.deepEqual(h.calls.fiscal, []);
  assert.match(h.calls.alerts[0], /Recarregue o produto/);
  assert.equal(h.form.ifood_pausado, true);
  h.env.failFiscal = false;
  await h.reload();
  await h.edit({ ifood_pausado: true });
  await h.submit();
  assert.equal(h.calls.products.length, 1);
  assert.deepEqual(h.calls.fiscal, []);
});

test("falha ao salvar edição fiscal bloqueia produto e mantém edição para tentar novamente", async () => {
  const h = await setup();
  await h.editFiscal("origem_mercadoria", "1");
  h.env.failSaveFiscal = true;
  await h.submit();
  assert.equal(h.calls.products.length, 0);
  assert.equal(h.form.tributacao.origem_mercadoria, "1");
  h.env.failSaveFiscal = false;
  await h.submit();
  assert.equal(h.calls.fiscal.length, 2);
  assert.equal(h.calls.products.length, 1);
});

test("recarregar mesmo produto com falha fiscal invalida a carga antiga", async () => {
  const h = await setup();
  h.env.failFiscal = true;
  await h.reload();
  await h.edit({ ifood_pausado: true });
  await h.submit();
  assert.deepEqual(h.calls.products, []);
  assert.deepEqual(h.calls.fiscal, []);
  assert.match(h.calls.alerts[0], /Recarregue o produto/);
});

test("trocar produto descarta edição fiscal anterior e usa o snapshot do novo ID", async () => {
  const h = await setup();
  await h.editFiscal("ncm", "12345678");
  await h.switchProduct({ id: 8, estoque_maximo: 0 }, { ncm: "87654321" });
  await h.edit({ ifood_pausado: true });
  await h.submit();
  assert.equal(h.form.tributacao.ncm, "87654321");
  assert.deepEqual(h.calls.fiscal, []);
  assert.equal(h.calls.products[0].id, 8);
  assert.equal(h.calls.products[0].body.estoque_maximo, 0);
});

const originalHtml =
  '<h2 style="color: red">Produto fictício</h2><p>Texto &amp; cuidados.<br>Uso diário.</p>';
const displayedDescription = "Produto fictício\nTexto & cuidados.\nUso diário.";

test("pausar e retomar pelo cadastro completo conserva HTML original e EANs não editados", async () => {
  const h = await setup({
    product: {
      descricao_curta: originalHtml,
      codigo_barras: "7890000000011",
      gtin_ean: "7890000000011",
      produto_identidade_id: null,
    },
  });
  assert.equal(h.form.descricao, displayedDescription);
  for (const paused of [true, false]) {
    await h.edit({ ifood_pausado: paused });
    await h.submit();
    const { body } = h.calls.products.at(-1);
    assert.equal(body.ifood_pausado, paused);
    assert.equal(body.descricao_curta, originalHtml);
    assert.equal(body.codigo_barras, "7890000000011");
    assert.equal(body.gtin_ean, "7890000000011");
    assert.equal(body.estoque_maximo, 0);
    assert.equal(Object.hasOwn(body, "produto_identidade_id"), false);
  }
  assert.equal(h.calls.products.length, 2);
  assert.equal(Object.keys(h.calls.products[0].body).length > 50, true);
  assert.deepEqual(h.calls.fiscal, []);
});

test("descrição realmente editada continua sendo normalizada e salva", async () => {
  const h = await setup({ product: { descricao_curta: originalHtml } });
  await h.edit({ descricao: "<p>Nova descrição &amp; instruções.</p>" });
  await h.submit();
  assert.equal(h.calls.products[0].body.descricao_curta, "Nova descrição & instruções.");
});

test("limpar uma descrição existente continua enviando null", async () => {
  const h = await setup({ product: { descricao_curta: originalHtml } });
  await h.edit({ descricao: "" });
  await h.submit();
  assert.equal(h.calls.products[0].body.descricao_curta, null);
});

test("editar e desfazer a descrição preserva exatamente o HTML salvo", async () => {
  const h = await setup({ product: { descricao_curta: originalHtml } });
  await h.edit({ descricao: "Mudança temporária" });
  await h.edit({ descricao: `  ${displayedDescription}\n` });
  await h.submit();
  assert.equal(h.calls.products[0].body.descricao_curta, originalHtml);
});

test("descrição original null ou string vazia conserva a distinção quando não editada", async () => {
  for (const original of [null, ""]) {
    const h = await setup({ product: { descricao_curta: original } });
    await h.edit({ ifood_pausado: true });
    await h.submit();
    assert.equal(h.calls.products[0].body.descricao_curta, original);
  }
});

test("sem descrição original definida a edição usa o conteúdo atual normalizado", async () => {
  const h = await setup();
  await h.edit({ descricao: "<p>Descrição preenchida agora.</p>" });
  await h.submit();
  assert.equal(h.calls.products[0].body.descricao_curta, "Descrição preenchida agora.");
});

test("criação continua normalizando a descrição, mesmo se o estado contém HTML original", async () => {
  const h = await setup({ isEdicao: false });
  await h.edit({ ...h.env.product, descricao_curta: originalHtml, descricao: originalHtml });
  await h.submit();
  assert.equal(h.calls.creates.length, 1);
  assert.equal(h.calls.creates[0].descricao_curta, displayedDescription);
  assert.deepEqual(h.calls.products, []);
});

test("clone carrega a descrição do produto de origem e mantém normalização no novo cadastro", async () => {
  const h = await setup({
    isEdicao: false,
    isClone: true,
    product: { descricao_curta: originalHtml },
  });
  assert.equal(h.form.descricao, originalHtml);
  await h.edit({ codigo: "DEV-CLONE", sku: "DEV-CLONE" });
  await h.submit();
  assert.equal(h.calls.creates.length, 1);
  assert.equal(h.calls.creates[0].descricao_curta, displayedDescription);
  assert.deepEqual(h.calls.products, []);
});
