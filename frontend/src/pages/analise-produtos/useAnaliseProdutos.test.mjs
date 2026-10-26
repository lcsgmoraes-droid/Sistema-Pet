import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";
import * as analiseUtils from "./analiseProdutosUtils.js";

const filtrosIniciais = {
  data_inicio: "2026-10-01",
  data_fim: "2026-10-26",
  categoria_id: "",
  marca_id: "",
  departamento_id: "",
  fornecedor_id: "",
  canal: "",
  busca: "",
};
const produto = {
  produto_id: 1,
  produto_nome: "Desinfetante vendido",
  codigo: "DOMIS-001",
  fornecedor_id: 7,
  fornecedor_nome: "QUIMIAGRI",
  quantidade: 12,
  faturamento: 240,
};

function pendente() {
  let resolve;
  let reject;
  const promise = new Promise((ok, erro) => {
    resolve = ok;
    reject = erro;
  });
  return { promise, resolve, reject };
}

function preparar({ gerarPdf } = {}) {
  const consultas = [],
    pdfs = [],
    salvos = [],
    downloads = [],
    blobs = [],
    avisos = [],
    erros = [];
  const empresa = { id: "empresa-atual", nome_fantasia: "Tecno Agropet" };
  const catalogos = {
    fornecedores: [{ id: 7, nome: "QUIMIAGRI" }],
    categorias: [],
    marcas: [],
    departamentos: [],
  };
  const toast = Object.assign((mensagem) => avisos.push({ tipo: "info", mensagem }), {
    error: (mensagem) => avisos.push({ tipo: "erro", mensagem }),
  });
  const pdf = { save: (nome) => salvos.push(nome) };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useAnaliseProdutos.js", import.meta.url)),
    {
      mocks: new Map([
        ["react-hot-toast", { __esModule: true, default: toast }],
        [
          "../../api/produtos",
          {
            getAnaliseProdutos: (filtros) => {
              const requisicao = { ...pendente(), filtros: { ...filtros } };
              consultas.push(requisicao);
              return requisicao.promise;
            },
            getRelatorioProdutoVendas: async () => ({ data: {} }),
          },
        ],
        ["../../hooks/useProdutosCatalogos", { __esModule: true, default: () => catalogos }],
        ["../../contexts/AuthContext", { useAuth: () => ({ user: { tenant: empresa } }) }],
        [
          "./analiseProdutosPdf.js",
          {
            criarPdfProdutosPorFornecedor: async (opcoes) => {
              pdfs.push(opcoes);
              return gerarPdf ? gerarPdf(opcoes, pdf) : pdf;
            },
          },
        ],
        [
          "./analiseProdutosUtils",
          { ...analiseUtils, criarFiltrosAnalise: () => ({ ...filtrosIniciais }) },
        ],
      ]),
      globals: {
        console: { error: (...args) => erros.push(args) },
        Blob,
        URL: {
          createObjectURL: (blob) => {
            blobs.push(blob);
            return `blob:relatorio-${blobs.length}`;
          },
          revokeObjectURL: () => {},
        },
        document: {
          createElement: (tag) => {
            assert.equal(tag, "a");
            return {
              click() {
                downloads.push({ href: this.href, nome: this.download });
              },
            };
          },
        },
      },
    },
  );
  return {
    harness,
    consultas,
    pdfs,
    salvos,
    downloads,
    blobs,
    avisos,
    erros,
    empresa,
    catalogos,
    pdf,
    async responder(indice, produtos = [produto]) {
      consultas[indice].resolve({ data: { produtos } });
      await harness.settle();
    },
  };
}

test("PDF e CSV usam dados e filtros aplicados mesmo com o formulário alterado sem aplicar", async () => {
  const env = preparar();
  await env.responder(0);
  await env.harness.act(() => {
    env.harness.tree.atualizarFiltro("fornecedor_id", "7");
    env.harness.tree.atualizarFiltro("data_inicio", "2026-01-01");
  });
  await env.harness.act(() => env.harness.tree.aplicarFiltros());
  await env.responder(1);
  const aplicados = { ...filtrosIniciais, fornecedor_id: "7", data_inicio: "2026-01-01" };

  await env.harness.act(() => {
    env.harness.tree.atualizarFiltro("fornecedor_id", "8");
    env.harness.tree.atualizarFiltro("data_inicio", "2025-01-01");
    env.harness.tree.atualizarFiltro("busca", "outro fornecedor ainda não aplicado");
  });
  await env.harness.act(() => env.harness.tree.exportarPdf());
  await env.harness.act(() => env.harness.tree.exportarCsv());

  assert.equal(env.consultas.length, 2);
  assert.equal(env.pdfs.length, 1);
  assert.deepEqual(env.pdfs[0].produtos, [produto]);
  assert.deepEqual(env.pdfs[0].filtros, aplicados);
  assert.equal(env.pdfs[0].empresa, env.empresa);
  assert.equal(env.pdfs[0].catalogos, env.catalogos);
  assert.deepEqual(env.salvos, ["produtos_vendidos_por_fornecedor_7_2026-01-01_2026-10-26.pdf"]);
  assert.equal(env.downloads[0].nome, "analise_produtos_2026-01-01_2026-10-26.csv");
  assert.match(await env.blobs[0].text(), /DOMIS-001/);
  assert.doesNotMatch(await env.blobs[0].text(), /outro fornecedor/);
});

test("exportações ficam bloqueadas no primeiro loading e durante a consulta de um novo filtro", async () => {
  const env = preparar();
  assert.equal(env.harness.tree.carregando, true);
  assert.equal(env.harness.tree.podeExportar, false);
  await env.harness.tree.exportarPdf();
  env.harness.tree.exportarCsv();
  assert.equal(env.pdfs.length, 0);
  assert.equal(env.downloads.length, 0);

  await env.responder(0);
  assert.equal(env.harness.tree.podeExportar, true);
  await env.harness.act(() => env.harness.tree.atualizarFiltro("fornecedor_id", "7"));
  await env.harness.act(() => env.harness.tree.aplicarFiltros());
  assert.equal(env.harness.tree.carregando, true);
  assert.equal(env.harness.tree.podeExportar, false);
  await env.harness.tree.exportarPdf();
  env.harness.tree.exportarCsv();
  assert.equal(env.pdfs.length, 0);
  assert.equal(env.downloads.length, 0);

  await env.responder(1);
  assert.equal(env.harness.tree.carregando, false);
  assert.equal(env.harness.tree.podeExportar, true);
});

test("falha de consulta não permite exportar resultado antigo com os novos filtros", async () => {
  const env = preparar();
  await env.responder(0);
  await env.harness.act(() => env.harness.tree.atualizarFiltro("fornecedor_id", "8"));
  await env.harness.act(() => env.harness.tree.aplicarFiltros());
  env.consultas[1].reject({ response: { data: { detail: "Falha ao consultar produtos" } } });
  await env.harness.settle();
  assert.equal(env.harness.tree.carregando, false);
  assert.equal(env.harness.tree.podeExportar, false);
  assert.deepEqual(env.harness.tree.dados.produtos, []);
  assert.ok(env.avisos.some((aviso) => aviso.mensagem === "Falha ao consultar produtos"));
  await env.harness.tree.exportarPdf();
  env.harness.tree.exportarCsv();
  assert.equal(env.pdfs.length, 0);
  assert.equal(env.downloads.length, 0);
});

test("resposta atrasada de uma consulta cancelada não substitui o fornecedor atual", async () => {
  const env = preparar();
  await env.harness.act(() => env.harness.tree.atualizarFiltro("fornecedor_id", "7"));
  await env.harness.act(() => env.harness.tree.aplicarFiltros());
  await env.responder(1);
  await env.responder(0, [
    { ...produto, produto_id: 99, produto_nome: "Produto de filtro antigo" },
  ]);
  assert.deepEqual(env.harness.tree.dados.produtos, [produto]);
  assert.equal(env.harness.tree.podeExportar, true);
  await env.harness.act(() => env.harness.tree.exportarPdf());
  assert.deepEqual(env.pdfs[0].produtos, [produto]);
  assert.equal(env.pdfs[0].filtros.fornecedor_id, "7");
});

test("datas incompletas ou invertidas não disparam consulta e mantêm o recorte aplicado", async () => {
  for (const datas of [
    { data_inicio: "", data_fim: "2026-10-26" },
    { data_inicio: "2026-10-01", data_fim: "" },
    { data_inicio: "2026-10-27", data_fim: "2026-10-01" },
  ]) {
    const env = preparar();
    await env.responder(0);
    await env.harness.act(() => {
      env.harness.tree.atualizarFiltro("data_inicio", datas.data_inicio);
      env.harness.tree.atualizarFiltro("data_fim", datas.data_fim);
    });
    let prevenido = false;
    await env.harness.act(() =>
      env.harness.tree.aplicarFiltros({
        preventDefault: () => {
          prevenido = true;
        },
      }),
    );
    assert.equal(prevenido, true);
    assert.equal(env.consultas.length, 1);
    assert.deepEqual(env.harness.tree.filtrosAplicados, filtrosIniciais);
    assert.ok(env.avisos.some((aviso) => aviso.tipo === "erro" && /data/i.test(aviso.mensagem)));
  }
});

test("recorte vazio não gera PDF ou download CSV", async () => {
  const env = preparar();
  await env.responder(0, []);
  assert.equal(env.harness.tree.carregando, false);
  assert.equal(env.harness.tree.podeExportar, false);
  await env.harness.tree.exportarPdf();
  env.harness.tree.exportarCsv();
  assert.equal(env.pdfs.length, 0);
  assert.equal(env.downloads.length, 0);
  assert.ok(env.avisos.some((aviso) => /Não há produtos/.test(aviso.mensagem)));
});

test("PDF mostra estado de geração, impede outra geração simultânea e libera para tentar após falha", async () => {
  const geracao = pendente();
  let tentativa = 0;
  const env = preparar({ gerarPdf: (_opcoes, pdf) => (++tentativa === 1 ? geracao.promise : pdf) });
  await env.responder(0);
  const exportacao = env.harness.tree.exportarPdf();
  await env.harness.settle();
  assert.equal(env.harness.tree.exportandoPdf, true);
  await env.harness.tree.exportarPdf();
  assert.equal(env.pdfs.length, 1);
  geracao.reject(new Error("Falha de geração simulada"));
  await exportacao;
  await env.harness.settle();
  assert.equal(env.harness.tree.exportandoPdf, false);
  assert.deepEqual(env.salvos, []);
  assert.ok(env.avisos.some((aviso) => /Não foi possível gerar o PDF/.test(aviso.mensagem)));
  await env.harness.act(() => env.harness.tree.exportarPdf());
  assert.equal(env.pdfs.length, 2);
  assert.equal(env.salvos.length, 1);
  assert.equal(env.harness.tree.exportandoPdf, false);
});
