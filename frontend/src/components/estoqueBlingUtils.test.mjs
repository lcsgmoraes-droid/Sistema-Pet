import assert from "node:assert/strict";
import test from "node:test";

import {
  buildSyncErrorMeta,
  buildSyncIssue,
  formatCacheAge,
  formatDurationMs,
  formatNumber,
  includesSearch,
} from "./estoqueBlingUtils.js";

test("formata numeros, idade de cache e duracao com fallbacks seguros", () => {
  assert.equal(formatNumber(1234.5678), "1.234,568");
  assert.equal(formatNumber("abc"), "-");

  assert.equal(formatCacheAge(0), "agora");
  assert.equal(formatCacheAge(59), "59s");
  assert.equal(formatCacheAge(120), "2 min");
  assert.equal(formatCacheAge(7200), "2 h");

  assert.equal(formatDurationMs(0), "agora");
  assert.equal(formatDurationMs(850), "850 ms");
  assert.equal(formatDurationMs(1200), "1.2 s");
  assert.equal(formatDurationMs(12500), "13 s");
});

test("busca textual normalizada em multiplos campos", () => {
  assert.equal(includesSearch("  bling  ", ["Produto sincronizado no Bling"]), true);
  assert.equal(includesSearch("sem termo", ["Produto sincronizado no Bling"]), false);
  assert.equal(includesSearch("", ["qualquer coisa"]), true);
});

test("classifica erros de sincronizacao do bling em mensagens acionaveis", () => {
  assert.deepEqual(
    buildSyncErrorMeta({
      ultimo_erro: "429 Too Many Requests",
      queue_status: "pendente",
    }),
    {
      category: "rate_limit",
      tone: "amber",
      title: "Aguardando janela segura do Bling",
      description:
        "O item ja entrou de novo na fila segura e sera retomado em lote menor. Abrir ou atualizar a pagina nao dispara esse erro; a tela mostra apenas o ultimo registro salvo.",
      buttonLabel: "Tentar item",
      action: "force",
      detailLabel: "Ultimo registro",
      detailValue: "Item aguardando nova janela segura para reenviar.",
      technicalValue: "429 TOO_MANY_REQUESTS",
    },
  );

  assert.equal(
    buildSyncErrorMeta(
      { ultimo_erro: "invalid_grant" },
      { blingConnected: true },
    ).category,
    "auth_resolved",
  );

  assert.equal(
    buildSyncErrorMeta({ ultimo_erro: "produto não encontrado no Bling" }).category,
    "not_found",
  );
  assert.equal(
    buildSyncErrorMeta({ ultimo_erro: "sem vínculo ativo com o Bling" }).category,
    "link",
  );
});

test("monta problema de sincronizacao priorizando fila, erro e divergencia", () => {
  assert.equal(
    buildSyncIssue(
      { ultimo_erro: "429 Too Many Requests", queue_status: "pendente" },
      {},
    ).category,
    "rate_limit",
  );

  assert.deepEqual(buildSyncIssue({ status: "ativo", divergencia: 0 }), null);

  const divergencia = buildSyncIssue({
    status: "ativo",
    estoque_sistema: 10,
    estoque_bling: 8,
    divergencia: 2,
  });

  assert.equal(divergencia.tone, "amber");
  assert.equal(divergencia.title, "Estoque divergente");
  assert.match(divergencia.description, /Sistema 10/);
  assert.match(divergencia.description, /Bling 8/);
});
