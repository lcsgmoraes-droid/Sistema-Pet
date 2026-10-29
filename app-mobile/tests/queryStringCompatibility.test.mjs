import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import decode from "decode-uri-component";
import { adaptQueryStringSource } from "../scripts/patch-query-string.mjs";

const require = createRequire(import.meta.url);
const queryString = require("query-string");
const getStateFromPath =
  require("@react-navigation/core/lib/commonjs/getStateFromPath.js").default;
const mobileRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);

test("adaptacao do decoder e idempotente e exige versoes e fonte conhecidas", () => {
  const original = "const decodeComponent = require('decode-uri-component');";
  const adapted = adaptQueryStringSource(original, "7.1.3", "0.5.1");
  assert.match(adapted, /require\('decode-uri-component'\)\.default/);
  assert.equal(adaptQueryStringSource(adapted, "7.1.3", "0.5.1"), adapted);
  for (const [source, query, decoder] of [
    [original, "8.0.0", "0.5.1"],
    [original, "7.1.3", "0.5.0"],
    [original + original, "7.1.3", "0.5.1"],
    ["fonte alterada", "7.1.3", "0.5.1"],
  ]) {
    assert.throws(() => adaptQueryStringSource(source, query, decoder));
  }
});

test("decoder corrigido preserva Unicode e decodifica uma vez entradas malformadas", () => {
  assert.equal(decode("Jo%C3%A3o%20%F0%9F%90%BE"), "João 🐾");
  assert.equal(decode("%25C2%zz"), "%C2%zz");
  assert.equal(decode("%25%41%zz"), "%A%zz");
  assert.equal(decode("%FE%FF"), "\uFFFD\uFFFD");
});

test("query-string real preserva acentos, espacos e parametros de retorno", () => {
  const parsed = queryString.parse(
    "nome=Jo%C3%A3o&termo=a+b&email=lucas%2Bpet%40example.com&ruim=%25C2%zz",
  );
  assert.deepEqual(
    { ...parsed },
    {
      nome: "João",
      termo: "a b",
      email: "lucas+pet@example.com",
      ruim: "%C2%zz",
    },
  );
  assert.equal(queryString.parse(queryString.stringify(parsed)).nome, "João");
});

test("React Navigation real interpreta o link usando o decoder corrigido", () => {
  const state = getStateFromPath(
    "/login?nome=Jo%C3%A3o&email=lucas%2Bpet%40example.com&ruim=%25C2%zz",
    { screens: { Login: "login" } },
  );
  assert.equal(state.routes[0].name, "Login");
  assert.deepEqual(state.routes[0].params, {
    nome: "João",
    email: "lucas+pet@example.com",
    ruim: "%C2%zz",
  });
});

test("payload de muitas sequencias distintas termina sem travar o processo", () => {
  const script = `
    import decode from 'decode-uri-component';
    import assert from 'node:assert/strict';
    let input = '';
    for (let i = 0; i < 32000; i++) {
      input += '%' + Math.floor(i / 256).toString(16).padStart(2, '0')
        + '%' + (i % 256).toString(16).padStart(2, '0') + 'x';
    }
    assert.ok(decode(input + '%zz').endsWith('%zz'));
  `;
  const child = spawnSync(
    process.execPath,
    ["--input-type=module", "-e", script],
    {
      cwd: mobileRoot,
      encoding: "utf8",
      timeout: 10000,
    },
  );
  assert.equal(child.error, undefined);
  assert.equal(child.status, 0, child.stderr);
});
