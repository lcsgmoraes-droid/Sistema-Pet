import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (name) => readFileSync(new URL(`./${name}`, import.meta.url), "utf8");

const cardSource = read("LembreteCard.jsx");
const listSource = read("LembretesList.jsx");
const pageSource = read("LembretesPage.jsx");
const modalSource = read("LembreteContatoModal.jsx");
const tabsSource = read("LembretesTabs.jsx");
const styleSource = read("../../styles/Lembretes.css");

test("central separa recompra, validade, relacionamento e relatórios", () => {
  for (const literal of ["Recompras", "Validade", "Relacionamento", "Histórico e relatórios"]) {
    assert.match(tabsSource, new RegExp(literal));
  }
  assert.match(pageSource, /Central de lembretes/);
  assert.doesNotMatch(pageSource, /LembretesBlingAutocadastros/);
  assert.doesNotMatch(pageSource, /LembretesDrePendentes/);
});

test("fila apresenta filtros exclusivos de prazo e tipo", () => {
  assert.match(listSource, /Cada faixa de prazo é exclusiva/);
  assert.match(listSource, /PRAZOS\.map/);
  assert.match(listSource, /Todos os tipos/);
  assert.match(listSource, /rounded-2xl border border-slate-200 bg-white/);
});

test("ações principais priorizam mensagem, push e histórico do ciclo", () => {
  assert.match(cardSource, /> Criar mensagem/);
  assert.match(cardSource, /Enviar notificação no app/);
  assert.match(
    cardSource,
    /Push indisponível\. Será habilitado quando o cliente tiver uma conta vinculada no app\./,
  );
  assert.match(cardSource, /contato\(s\) neste ciclo/);
  assert.match(cardSource, /Registrar recompra/);
  assert.doesNotMatch(cardSource, /className="btn /);
});

test("compositor deixa sugestão editável e distingue abertura do WhatsApp", () => {
  assert.match(modalSource, /textarea/);
  assert.match(modalSource, /Abrir WhatsApp/);
  assert.match(modalSource, /Enviar push/);
  assert.match(modalSource, /Conversa aberta/);
  assert.match(modalSource, /Histórico deste ciclo/);
});

test("folha da página continua sem estilos legados de cartão", () => {
  assert.doesNotMatch(styleSource, /\.lembrete-card/);
  assert.doesNotMatch(styleSource, /\.section-title/);
  assert.doesNotMatch(styleSource, /\.btn-primary/);
});
