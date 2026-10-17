import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (name) => readFileSync(new URL(`./${name}`, import.meta.url), "utf8");

const cardSource = read("LembreteCard.jsx");
const birthdaySource = read("LembretesAniversariantes.jsx");
const listSource = read("LembretesList.jsx");
const pageSource = read("LembretesPage.jsx");
const inactiveSource = read("LembretesClientesInativos.jsx");
const modalSource = read("LembreteContatoModal.jsx");
const tabsSource = read("LembretesTabs.jsx");
const blingSource = read("LembretesBlingAutocadastros.jsx");

test("central separa as áreas, com as abas só de consulta antes das que alteram dados", () => {
  const ordem = ["relatorios", "bling", "relacionamento", "aniversarios", "recompras", "validade"];
  const posicoes = ordem.map((id) => tabsSource.indexOf(`id: "${id}"`));
  assert.ok(
    posicoes.every((posicao) => posicao >= 0),
    "toda aba deve existir",
  );
  assert.deepEqual(
    posicoes,
    [...posicoes].sort((a, b) => a - b),
    "abas devem seguir a ordem: consulta primeiro, alteração à direita",
  );
  for (const literal of ["Recompras", "Validade", "Aniversários", "Relacionamento", "Relatórios"]) {
    assert.match(tabsSource, new RegExp(literal));
  }
  assert.match(tabsSource, /id: "aniversarios"[^}]+contador: controller\.aniversariantes\.length/);
  assert.match(tabsSource, /controller\.blingAtivo &&/);
  assert.match(pageSource, /Central de lembretes/);
  assert.match(pageSource, /LembretesBlingAutocadastros/);
  assert.doesNotMatch(pageSource, /LembretesDrePendentes/);
});

test("tela usa apenas componentes v2 para campos e botões", () => {
  for (const source of [cardSource, listSource, modalSource, birthdaySource, inactiveSource]) {
    assert.doesNotMatch(source, /<(input|select|textarea|button)[\s>]/);
  }
});

test("fila apresenta filtros exclusivos de prazo e tipo", () => {
  assert.match(listSource, /Cada faixa de prazo é exclusiva/);
  assert.match(listSource, /PRAZOS\.map/);
  assert.match(listSource, /Todos os tipos/);
});

test("ações principais priorizam mensagem e deixam o resto no menu de ações", () => {
  assert.match(cardSource, /Criar mensagem/);
  assert.match(cardSource, /Enviar notificação no app/);
  assert.match(
    cardSource,
    /Push indisponível: será habilitado quando o cliente tiver uma conta vinculada no app\./,
  );
  assert.match(cardSource, /contato\(s\) neste ciclo/);
  assert.match(cardSource, /Registrar recompra/);
  assert.match(cardSource, /Criar próximo ciclo/);
  assert.match(cardSource, /Cancelar lembrete/);
  assert.match(cardSource, /BotaoMenuAcoes/);
});

test("compositor deixa sugestão editável e distingue abertura do WhatsApp", () => {
  assert.match(modalSource, /InputTextoLongo/);
  assert.match(modalSource, /ModalPadrao/);
  assert.match(modalSource, /Abrir WhatsApp/);
  assert.match(modalSource, /Enviar push/);
  assert.match(modalSource, /Conversa aberta/);
  assert.match(modalSource, /Histórico deste ciclo/);
});

test("relacionamento lista clientes inativos com ações manuais de mensagem", () => {
  assert.match(pageSource, /LembretesClientesInativos/);
  assert.match(inactiveSource, /Clientes inativos/);
  assert.match(inactiveSource, /\[30, 60, 90\]/);
  assert.match(inactiveSource, /\+ dias/);
  assert.match(inactiveSource, /Abrir WhatsApp/);
  assert.match(inactiveSource, /Copiar mensagem/);
  assert.match(inactiveSource, /Nenhuma mensagem é\s+enviada automaticamente/);
});

test("aba própria oferece aniversários de tutor e pet com mensagem, push e WhatsApp", () => {
  assert.match(pageSource, /abaAtiva === "aniversarios"/);
  assert.match(pageSource, /LembretesAniversariantes/);
  assert.match(birthdaySource, /Aniversariantes — tutor e pet/);
  assert.match(birthdaySource, /Criar mensagem/);
  assert.match(birthdaySource, /Enviar novamente uma notificação no app/);
  assert.match(modalSource, /Abrir WhatsApp/);
  assert.match(modalSource, /reminder\.historico_titulo/);
});

test("aba Bling mostra os cadastros automáticos das últimas 24 horas", () => {
  assert.match(blingSource, /Auto cadastro Bling/);
  assert.match(blingSource, /últimas 24 horas/);
});
