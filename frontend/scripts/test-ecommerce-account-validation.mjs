import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const accountPage = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/EcommerceAccountPage.jsx"),
  "utf8",
);
const customerHook = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/useEcommerceCustomer.js"),
  "utf8",
);
const ordersHook = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/useEcommerceOrders.js"),
  "utf8",
);
const ordersPage = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/EcommerceOrdersPage.jsx"),
  "utf8",
);

assert.match(
  accountPage,
  /function FieldError/,
  "cadastro deve renderizar mensagens de erro perto do campo",
);

assert.match(
  accountPage,
  /fieldInputStyle\(S\.formInput, registerFieldError, "nome"\)/,
  "campo nome do cadastro deve receber destaque visual quando invalido",
);

assert.match(
  customerHook,
  /focusEcommerceField\("ecommerce_register_", field\)/,
  "validacao de cadastro deve levar o foco ao campo incorreto",
);

assert.match(
  customerHook,
  /field:\s*"nome",\s*message:\s*"Informe nome completo \(nome e sobrenome\)\./,
  "cadastro deve validar nome completo antes de chamar a API",
);

assert.match(
  customerHook,
  /getRegisterValidation\(registerForm, tenantContext\)/,
  "cadastro deve centralizar a validacao antes de chamar a API",
);

assert.match(
  customerHook,
  /inferRegisterFieldFromMessage/,
  "erros vindos do backend devem ser associados a campos do cadastro",
);

assert.match(
  ordersHook,
  /const \[ordersError, setOrdersError\]/,
  "pedidos deve guardar erro proprio de carregamento",
);

assert.match(
  ordersPage,
  /Nao foi possivel carregar pedidos/,
  "pagina de pedidos deve comunicar falha no corpo da tela",
);

assert.match(
  ordersPage,
  /Tentar novamente/,
  "pagina de pedidos deve oferecer recarregar quando a lista falhar",
);

console.log("E-commerce account validation checks passed.");
