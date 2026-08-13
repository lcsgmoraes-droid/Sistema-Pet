import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (name) => readFileSync(new URL(`./${name}`, import.meta.url), "utf8");

const cardSource = read("LembreteCard.jsx");
const listSource = read("LembretesList.jsx");
const headerSource = read("LembretesHeader.jsx");
const campaignsSource = read("LembretesCampanhasAlertas.jsx");
const blingSource = read("LembretesBlingAutocadastros.jsx");
const dreSource = read("LembretesDrePendentes.jsx");
const styleSource = read("../../styles/Lembretes.css");

test("recorrencias seguem o mesmo cartao clean da area de validade", () => {
  assert.match(cardSource, /rounded-xl border border-slate-200 bg-white/);
  assert.match(cardSource, /dark:border-slate-700 dark:bg-slate-900/);
  assert.match(cardSource, /formatarMoeda\(lembrete\.preco_estimado\)/);
  assert.doesNotMatch(cardSource, /className="btn /);
  assert.doesNotMatch(cardSource, /toFixed\(2\)/);
});

test("secoes de recorrencia usam cabecalho, contador e grade padronizados", () => {
  assert.match(listSource, /rounded-2xl border border-slate-200 bg-white/);
  assert.match(listSource, /\{lembretes\.length\} \{lembretes\.length === 1/);
  assert.match(listSource, /dark:border-slate-700 dark:bg-slate-900/);
  assert.doesNotMatch(listSource, /className="section/);
});

test("folha da pagina nao conserva seletores visuais do cartao antigo", () => {
  assert.doesNotMatch(styleSource, /\.lembrete-card/);
  assert.doesNotMatch(styleSource, /\.section-title/);
  assert.doesNotMatch(styleSource, /\.btn-primary/);
});

test("cabecalho e paineis auxiliares abandonam estilos antigos em linha", () => {
  assert.match(headerSource, /rounded-2xl border border-slate-200/);
  assert.doesNotMatch(campaignsSource, /style=\{\{/);
  assert.doesNotMatch(blingSource, /style=\{\{/);
  assert.doesNotMatch(dreSource, /style=\{\{/);
});

test("acoes mantem semantica com visual operacional consistente", () => {
  assert.match(cardSource, />\s*Comprado\s*</);
  assert.match(cardSource, />\s*Renovar\s*</);
  assert.match(cardSource, /rounded-lg border border-teal-700 bg-teal-700/);
  assert.match(cardSource, /rounded-lg border border-slate-200 bg-white/);
});
