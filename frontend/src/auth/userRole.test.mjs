import assert from "node:assert/strict";

import { getDefaultAuthenticatedRoute, isAdminRole } from "./userRole.js";

assert.equal(isAdminRole({ role: { name: "Admin" } }), true);
assert.equal(isAdminRole({ role: { name: "Administrador" } }), true);
assert.equal(isAdminRole({ role: { name: "Gerente" } }), false);

assert.equal(getDefaultAuthenticatedRoute({ role: { name: "Administrador" } }), "/dashboard");
assert.equal(getDefaultAuthenticatedRoute({ role: { name: "Gerente" } }), "/dashboard");
assert.equal(getDefaultAuthenticatedRoute({ role: { name: "Caixa" } }), "/pdv");
assert.equal(getDefaultAuthenticatedRoute({ role: { name: "Vendedor" } }), "/lembretes");
