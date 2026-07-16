import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import vm from "node:vm";
import ts from "typescript";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

function carregarModuloTs(relativo) {
  const arquivo = path.resolve(__dirname, "..", relativo);
  const fonte = readFileSync(arquivo, "utf8");
  const { outputText } = ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  });
  const module = { exports: {} };
  vm.runInNewContext(
    outputText,
    {
      module,
      exports: module.exports,
      require,
    },
    { filename: arquivo },
  );
  return module.exports;
}

test("extrai produto da notificacao de estoque por produto_id ou product_id", () => {
  const { stockNotificationToProductId } = carregarModuloTs(
    "src/utils/notificationNavigation.ts",
  );

  assert.equal(
    stockNotificationToProductId({
      source: "stock_waitlist",
      kind: "stock_available",
      produto_id: "6089",
    }),
    6089,
  );
  assert.equal(
    stockNotificationToProductId({
      source: "stock_waitlist",
      kind: "stock_available",
      product_id: 1715,
    }),
    1715,
  );
  assert.equal(
    stockNotificationToProductId({
      type: "stock_available",
      product_id: "2291",
    }),
    2291,
  );
  assert.equal(stockNotificationToProductId({ source: "order" }), null);
  assert.equal(
    stockNotificationToProductId({
      source: "stock_waitlist",
      kind: "stock_available",
      produto_id: "abc",
    }),
    null,
  );
});

test("abre o produto certo ao tocar no lembrete de recompra", () => {
  const { recurrenceNotificationToProductId } = carregarModuloTs(
    "src/utils/notificationNavigation.ts",
  );

  assert.equal(
    recurrenceNotificationToProductId({
      source: "product_recurrence",
      kind: "repurchase_due",
      produto_id: "6089",
    }),
    6089,
  );
  assert.equal(
    recurrenceNotificationToProductId({
      source: "product_recurrence",
      kind: "repurchase_due",
      product_id: 1715,
    }),
    1715,
  );
  assert.equal(recurrenceNotificationToProductId({ source: "campaign" }), null);
});

test("direciona lembretes de agendamento para a area certa do app", () => {
  const { appointmentNotificationTarget } = carregarModuloTs(
    "src/utils/notificationNavigation.ts",
  );

  const banhoTosaTarget = appointmentNotificationTarget({
    source: "appointment_reminder",
    kind: "banho_tosa_agendamento",
    module: "banho_tosa",
    agendamento_id: "33",
  });
  assert.equal(banhoTosaTarget.route, "Pets");
  assert.equal(banhoTosaTarget.params.screen, "BanhoTosa");

  const vetTarget = appointmentNotificationTarget({
    source: "appointment_reminder",
    kind: "veterinario_agendamento",
    module: "veterinario",
    appointment_id: 44,
  });
  assert.equal(vetTarget.route, "Pets");
  assert.equal(vetTarget.params.screen, "Veterinario");
  assert.equal(appointmentNotificationTarget({ source: "order" }), null);
});

test("direciona campanhas para beneficios, cupons ou banho e tosa", () => {
  const { campaignNotificationTarget } = carregarModuloTs(
    "src/utils/notificationNavigation.ts",
  );

  const birthdayTarget = campaignNotificationTarget({
    source: "campaign",
    kind: "birthday_customer",
    target: "coupons",
    coupon_code: "ANIV-123",
  });
  assert.equal(birthdayTarget.route, "Beneficios");
  assert.equal(birthdayTarget.params.screen, "MeusCupons");

  const cashbackTarget = campaignNotificationTarget({
    source: "campaign",
    kind: "cashback",
    target: "benefits",
  });
  assert.equal(cashbackTarget.route, "Beneficios");
  assert.equal(cashbackTarget.params.screen, "MeusBeneficios");

  const retornoTarget = campaignNotificationTarget({
    source: "campaign",
    kind: "banho_tosa_retorno",
    target: "banho_tosa",
  });
  assert.equal(retornoTarget.route, "Pets");
  assert.equal(retornoTarget.params.screen, "BanhoTosa");
  assert.equal(campaignNotificationTarget({ source: "order" }), null);
});

test("central de notificacoes mobile chama endpoints do app", () => {
  const serviceSource = readFileSync(
    path.resolve(__dirname, "../src/services/appNotifications.service.ts"),
    "utf8",
  );
  const screenSource = readFileSync(
    path.resolve(__dirname, "../src/screens/notifications/NotificationsScreen.tsx"),
    "utf8",
  );

  assert.match(serviceSource, /api\.get\(["']\/app\/notificacoes["']\)/);
  assert.match(serviceSource, /api\.post\(`\/app\/notificacoes\/\$\{id\}\/lida`\)/);
  assert.match(serviceSource, /api\.delete\(["']\/app\/notificacoes["']\)/);
  assert.match(screenSource, /limparNotificacoesApp/);
  assert.match(screenSource, /markNotificationAsRead/);
  assert.match(screenSource, /stockNotificationToProductId/);
  assert.match(screenSource, /campaignNotificationTarget/);
  assert.match(screenSource, /gift-outline/);
});

test("home mobile mostra badge vermelho com notificacoes nao lidas", () => {
  const homeSource = readFileSync(
    path.resolve(__dirname, "../src/screens/HomeScreen.tsx"),
    "utf8",
  );

  assert.match(homeSource, /listarNotificacoesApp/);
  assert.match(homeSource, /useFocusEffect/);
  assert.match(homeSource, /unreadNotifications/);
  assert.match(homeSource, /notificacoesBadge/);
  assert.match(homeSource, /99\+/);
});

test("detalhe do produto ignora produto antigo quando notificacao envia outro produtoId", () => {
  const { resolveProductDetailParams } = carregarModuloTs(
    "src/utils/productDetailRoute.ts",
  );

  const produtoAntigo = { id: 5107, nome: "Produto antigo" };
  const resultado = resolveProductDetailParams({
    produto: produtoAntigo,
    produtoId: 6089,
  });

  assert.equal(resultado.produtoId, 6089);
  assert.equal(resultado.produtoParam, undefined);
});

test("detalhe de produto indisponivel no app orienta ecommerce e loja fisica", () => {
  const {
    buildEcommerceSearchUrl,
    isProductAvailableInApp,
    isProductAvailableInEcommerce,
  } = carregarModuloTs("src/utils/productAvailability.ts");

  assert.equal(
    isProductAvailableInApp({ anunciar_app: false, disponivel_app: false }),
    false,
  );
  assert.equal(isProductAvailableInApp({ anunciar_app: true }), true);
  assert.equal(
    isProductAvailableInEcommerce({
      anunciar_ecommerce: true,
      disponivel_ecommerce: true,
      estoque: 2,
    }),
    true,
  );
  assert.equal(
    isProductAvailableInEcommerce({
      anunciar_ecommerce: true,
      disponivel_ecommerce: false,
      estoque: 2,
    }),
    false,
  );
  assert.equal(
    isProductAvailableInEcommerce({
      anunciar_ecommerce: true,
      disponivel_ecommerce: true,
      estoque: 0,
    }),
    false,
  );
  assert.equal(
    buildEcommerceSearchUrl({
      apiBaseUrl: "https://corepet.com.br/api",
      tenantSlug: "atacadaopetpp",
      query: "SKU 6089",
    }),
    "https://corepet.com.br/atacadaopetpp?busca=SKU%206089",
  );

  const detailSource = readFileSync(
    path.resolve(__dirname, "../src/screens/shop/ProductDetailScreen.tsx"),
    "utf8",
  );
  assert.match(detailSource, /produtoDisponivelNoApp/);
  assert.match(detailSource, /produtoDisponivelNoEcommerce/);
  assert.match(detailSource, /Esse produto chegou na loja/);
  assert.match(detailSource, /Pesquisar no e-commerce/);
  assert.match(detailSource, /loja fisica/);
  assert.match(detailSource, /openEcommerceSearch/);
  assert.match(detailSource, /produtoDisponivelNoEcommerce && ecommerceSearchUrl/);
});

test("login e cadastro usam autofill seguro do celular", () => {
  const loginSource = readFileSync(
    path.resolve(__dirname, "../src/screens/auth/LoginScreen.tsx"),
    "utf8",
  );
  const registerSource = readFileSync(
    path.resolve(__dirname, "../src/screens/auth/RegisterScreen.tsx"),
    "utf8",
  );

  assert.match(loginSource, /autoComplete="email"/);
  assert.match(loginSource, /textContentType="username"/);
  assert.match(loginSource, /autoComplete="current-password"/);
  assert.match(loginSource, /textContentType="password"/);
  assert.match(loginSource, /importantForAutofill="yes"/);

  assert.match(registerSource, /autoComplete="email"/);
  assert.match(registerSource, /textContentType="username"/);
  assert.match(registerSource, /autoComplete="new-password"/);
  assert.match(registerSource, /textContentType="newPassword"/);
  assert.match(registerSource, /passwordRules=/);
});
