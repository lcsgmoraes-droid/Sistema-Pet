import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function readSource(relativePath) {
  return readFileSync(path.resolve(__dirname, "..", relativePath), "utf8");
}

test("troca de perfil usa lista propria sem o limite de tres botoes do Android", () => {
  const modal = readSource("src/components/ProfileSwitcherModal.tsx");
  const header = readSource("src/components/HeaderProfileActions.tsx");
  const profile = readSource("src/screens/profile/ProfileScreen.tsx");

  assert.match(modal, /<Modal/);
  assert.match(modal, /<ScrollView/);
  assert.match(modal, /profiles\.map/);
  assert.match(modal, />Cancelar</);
  assert.match(header, /<ProfileSwitcherModal/);
  assert.match(profile, /<ProfileSwitcherModal/);
  assert.doesNotMatch(header, /Alert\.alert\("Trocar perfil"[^;]*profileOptions/s);
  assert.doesNotMatch(profile, /Alert\.alert\("Trocar perfil"[^;]*profileOptions/s);
});
