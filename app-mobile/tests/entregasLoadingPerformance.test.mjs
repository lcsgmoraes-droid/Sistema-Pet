import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const root = path.resolve(import.meta.dirname, "..");

function source(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

test("a abertura das entregas nao espera o historico completo", () => {
  const screen = source("src/screens/entregador/RotasDoEntregadorScreen.tsx");
  const carregarInicio = screen.indexOf("const carregar = useCallback");
  const carregarHistoricoInicio = screen.indexOf(
    "const carregarHistorico = useCallback",
  );
  const carregarInicial = screen.slice(carregarInicio, carregarHistoricoInicio);
  const carregarHistorico = screen.slice(carregarHistoricoInicio);

  assert.ok(carregarInicio >= 0);
  assert.ok(carregarHistoricoInicio > carregarInicio);
  assert.doesNotMatch(carregarInicial, /status:\s*["']concluida["']/);
  assert.match(carregarHistorico, /status:\s*["']concluida["']/);
  assert.match(screen, /onPress=\{abrirHistorico\}/);
});
