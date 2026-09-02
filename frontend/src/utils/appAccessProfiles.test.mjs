import assert from "node:assert/strict";
import { test } from "node:test";
import { canManageAppAccessProfiles } from "./appAccessProfiles.js";

test("administrador pode gerenciar perfis do app", () => {
  assert.equal(
    canManageAppAccessProfiles({ role: { name: "Administrador" }, permissions: [] }),
    true,
  );
});

test("permissao administrativa permite gerenciar perfis do app", () => {
  assert.equal(
    canManageAppAccessProfiles({
      role: { name: "Personalizado" },
      permissions: ["usuarios.manage"],
    }),
    true,
  );
});

test("usuario comum nao pode gerenciar perfis do app", () => {
  assert.equal(
    canManageAppAccessProfiles({
      role: { name: "Gerente" },
      permissions: ["rh.funcionarios", "clientes.editar"],
    }),
    false,
  );
});
