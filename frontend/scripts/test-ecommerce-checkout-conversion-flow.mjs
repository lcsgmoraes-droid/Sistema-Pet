import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const checkoutPage = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/EcommerceCheckoutPage.jsx"),
  "utf8",
);
const checkoutHook = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/useEcommerceCheckout.js"),
  "utf8",
);
const customerHook = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/useEcommerceCustomer.js"),
  "utf8",
);
const ecommerceMvp = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/EcommerceMVP.jsx"),
  "utf8",
);
const styles = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/ecommerceMvpStyles.js"),
  "utf8",
);

assert.match(
  checkoutPage,
  /function CheckoutMobilePaymentBar/,
  "checkout deve ter uma barra fixa de pagamento para telas pequenas",
);

assert.match(
  checkoutPage,
  /finalizeBlockReason/,
  "checkout deve explicar por que o pagamento ainda nao pode ser iniciado",
);

assert.match(
  checkoutPage,
  /!pagamentoTipo/,
  "botao de pagamento deve ficar bloqueado ate a forma de pagamento ser escolhida",
);

assert.match(
  styles,
  /checkoutSummaryBox:\s*\(isMobile\)\s*=>/,
  "resumo do checkout deve ter estilo proprio para grudar no desktop",
);

assert.match(
  styles,
  /position:\s*isMobile\s*\?\s*"static"\s*:\s*"sticky"/,
  "resumo do checkout deve acompanhar a rolagem no desktop",
);

assert.match(styles, /mobileCheckoutBar:/, "checkout deve definir estilo da barra fixa mobile");

assert.match(
  ecommerceMvp,
  /const\s+\[authReturnView,\s*setAuthReturnView\]\s*=\s*useState\(["']["']\)/,
  "pagina deve guardar a tela pretendida antes de exigir login",
);

assert.match(
  ecommerceMvp,
  /onRequireAuthForCheckout:\s*requireAuthForCheckout/,
  "checkout deve registrar a intencao de voltar ao pagamento ao exigir login",
);

assert.match(
  checkoutHook,
  /onRequireAuthForCheckout\(\)/,
  "hook de checkout deve usar o callback dedicado quando login for necessario",
);

assert.match(
  customerHook,
  /resolvePostAuthView/,
  "login deve decidir a tela pos-autenticacao com base na intencao e no cadastro",
);

assert.match(
  customerHook,
  /setView\(nextView\)/,
  "login deve navegar para a tela calculada, nao sempre para Conta",
);

console.log("E-commerce checkout conversion flow checks passed.");
