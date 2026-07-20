import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(__dirname, "..");

function read(relativePath) {
  return readFileSync(path.join(appRoot, relativePath), "utf8");
}

test("servico mobile envia senha e confirmacao para exclusao definitiva", () => {
  const source = read("src/services/auth.service.ts");

  assert.match(source, /api\.delete[^]*['"]\/ecommerce\/auth\/conta['"]/);
  assert.match(source, /confirmation:\s*['"]EXCLUIR['"]/);
});

test("perfil exige senha e confirmacao explicita antes de excluir", () => {
  const source = read(
    "src/screens/profile/profile/ProfilePersonalSections.tsx",
  );

  assert.match(source, /Excluir minha conta/);
  assert.match(source, /secureTextEntry/);
  assert.match(source, /Digite EXCLUIR/);
  assert.match(source, /Excluir conta definitivamente/);
  assert.match(source, /Esta acao nao pode ser desfeita/);
});

test("exclusao confirmada limpa carrinho favoritos e autenticacao local", () => {
  const source = read("src/screens/profile/ProfileScreen.tsx");

  assert.match(source, /AuthService\.deleteAccount\(password\)/);
  assert.match(source, /useCartStore\.getState\(\)\.limparLocal\(\)/);
  assert.match(source, /useWishlistStore\.getState\(\)\.limpar\(\)/);
  assert.match(source, /await logout\(\)/);
});
