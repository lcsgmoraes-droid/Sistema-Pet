import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import vm from "node:vm";
import ts from "typescript";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

function carregarModuloTs(relativo) {
  const arquivo = path.resolve(__dirname, "..", relativo);
  const fonte = readFileSync(arquivo, "utf8");
  const { outputText } = ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  });
  const module = { exports: {} };
  vm.runInNewContext(
    outputText,
    {
      module,
      exports: module.exports,
      require,
    },
    { filename: arquivo },
  );
  return module.exports;
}

const { compartilharArquivoGerado } = carregarModuloTs(
  "src/services/funcionarioContagemArquivo.ts",
);

test("compartilha arquivo no Android usando modulo nativo e content uri", async () => {
  const chamadas = [];

  await compartilharArquivoGerado(
    { filename: "contagem-1.pdf", mime_type: "application/pdf" },
    {
      uri: "file:///data/user/0/app/cache/contagem-1.pdf",
      contentUri: "content://br.com.corepet.app.FileSystemFileProvider/cache/contagem-1.pdf",
    },
    {
      platform: "android",
      nativeShare: {
        shareFile: async (...args) => {
          chamadas.push(args);
        },
      },
      share: async () => {
        throw new Error("Share de texto nao deve ser chamado no Android");
      },
    },
  );

  assert.deepEqual(chamadas, [
    [
      "content://br.com.corepet.app.FileSystemFileProvider/cache/contagem-1.pdf",
      "application/pdf",
      "contagem-1.pdf",
    ],
  ]);
});

test("bloqueia envio no Android sem modulo nativo para evitar link file", async () => {
  await assert.rejects(
    () =>
      compartilharArquivoGerado(
        { filename: "contagem-1.xlsx", mime_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
        { uri: "file:///data/user/0/app/cache/contagem-1.xlsx" },
        {
          platform: "android",
          nativeShare: undefined,
          share: async () => {
            throw new Error("Share de texto nao deve ser chamado no Android");
          },
        },
      ),
    /atualize o aplicativo/i,
  );
});

test("mantem compartilhamento por url no iOS", async () => {
  let conteudo = null;

  await compartilharArquivoGerado(
    { filename: "contagem-1.pdf", mime_type: "application/pdf" },
    { uri: "file:///cache/contagem-1.pdf" },
    {
      platform: "ios",
      nativeShare: undefined,
      share: async (entrada) => {
        conteudo = entrada;
      },
    },
  );

  assert.equal(conteudo.title, "contagem-1.pdf");
  assert.equal(conteudo.url, "file:///cache/contagem-1.pdf");
});
