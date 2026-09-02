import assert from "node:assert/strict";
import test from "node:test";
import {
  COREPET_STORE_URLS,
  buildAppInstallLinks,
  getAppInstallPlatform,
  openAppWithStoreFallback,
} from "./appInstallLinks.js";

test("reconhece Android, iPhone, iPad e computadores sem escolher a loja errada", () => {
  for (const [userAgent, maxTouchPoints, expected] of [
    ["Mozilla/5.0 (Linux; Android 14) Chrome/130.0 Mobile Safari/537.36", 5, "android"],
    ["Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15", 5, "ios"],
    ["Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X)", 5, "ios"],
    ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Version/18.0 Safari/605.1.15", 5, "ios"],
    ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)", 0, null],
    ["Mozilla/5.0 (Windows NT 10.0; Win64; x64)", 10, null],
    ["", 0, null],
  ]) {
    assert.equal(getAppInstallPlatform({ userAgent, maxTouchPoints }), expected, userAgent);
  }
});

test("Android abre o pacote CorePet com a loja escolhida e download como alternativa", () => {
  const links = buildAppInstallLinks("atacadao", "android");
  assert.equal(links.storeUrl, "https://play.google.com/store/apps/details?id=br.com.corepet.app");
  const [destination, intent] = links.openUrl.split("#Intent;");
  assert.equal(destination, "intent://app?loja=atacadao");
  assert.ok(intent.includes("scheme=corepet;package=br.com.corepet.app;"));
  const fallback = intent.match(/S\.browser_fallback_url=([^;]+);/)[1];
  assert.equal(decodeURIComponent(fallback), links.storeUrl);
});

test("iOS mantém o deep link instalado e usa a página oficial do CorePet", () => {
  assert.deepEqual(buildAppInstallLinks("outra-loja", "ios"), {
    openUrl: "corepet://app?loja=outra-loja",
    storeUrl: "https://apps.apple.com/br/app/corepet/id6785267892",
  });
});

test("o código da loja não pode injetar outro destino no intent", () => {
  const slug = "loja&outro=1#Intent;package=outro;end";
  const { openUrl } = buildAppInstallLinks(slug, "android");
  const [destination] = openUrl.split("#Intent;");
  assert.equal(new URL(destination).searchParams.get("loja"), slug);
  assert.equal(openUrl.split("#Intent;").length, 2);
});

function setupBrowser(t) {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const navigations = [];
  const browser = new EventTarget();
  browser.document = new EventTarget();
  browser.document.visibilityState = "visible";
  browser.location = { assign: (url) => navigations.push(url) };
  browser.setTimeout = setTimeout;
  browser.clearTimeout = clearTimeout;
  return { browser, navigations };
}

for (const platform of ["android", "ios"]) {
  test(`${platform}: encaminha para download quando a tentativa não abre o app`, (t) => {
    const { browser, navigations } = setupBrowser(t);
    const links = buildAppInstallLinks("atacadao", platform);
    openAppWithStoreFallback(links, browser);
    assert.deepEqual(navigations, [links.openUrl]);
    t.mock.timers.runAll();
    assert.deepEqual(navigations, [links.openUrl, COREPET_STORE_URLS[platform]]);
  });
}

test("voltar do app instalado não abre a loja de aplicativos", (t) => {
  const { browser, navigations } = setupBrowser(t);
  const links = buildAppInstallLinks("atacadao", "ios");
  openAppWithStoreFallback(links, browser);
  browser.document.visibilityState = "hidden";
  browser.document.dispatchEvent(new Event("visibilitychange"));
  browser.document.visibilityState = "visible";
  browser.document.dispatchEvent(new Event("visibilitychange"));
  t.mock.timers.runAll();
  assert.deepEqual(navigations, [links.openUrl]);
});

test("sair da página cancela o encaminhamento pendente", (t) => {
  const { browser, navigations } = setupBrowser(t);
  const links = buildAppInstallLinks("atacadao", "ios");
  openAppWithStoreFallback(links, browser);
  browser.dispatchEvent(new Event("pagehide"));
  t.mock.timers.runAll();
  assert.deepEqual(navigations, [links.openUrl]);
});

test("perda de foco sem abrir o app não impede o download, como em um aviso de app ausente", (t) => {
  const { browser, navigations } = setupBrowser(t);
  const links = buildAppInstallLinks("atacadao", "ios");
  openAppWithStoreFallback(links, browser);
  browser.dispatchEvent(new Event("blur"));
  browser.dispatchEvent(new Event("focus"));
  t.mock.timers.runAll();
  assert.deepEqual(navigations, [links.openUrl, links.storeUrl]);
});

test("cancelar ao comprar online, escolher download ou desmontar a página impede redirecionamento", (t) => {
  const { browser, navigations } = setupBrowser(t);
  const links = buildAppInstallLinks("atacadao", "android");
  const cancel = openAppWithStoreFallback(links, browser);
  cancel();
  cancel();
  t.mock.timers.runAll();
  assert.deepEqual(navigations, [links.openUrl]);
});

test("computador não tenta abrir um aplicativo mobile nem escolhe uma loja automaticamente", (t) => {
  const { browser, navigations } = setupBrowser(t);
  openAppWithStoreFallback(buildAppInstallLinks("atacadao", null), browser);
  t.mock.timers.runAll();
  assert.deepEqual(navigations, []);
});

test("erro imediato ao abrir o app encaminha para a loja uma única vez", (t) => {
  const { browser, navigations } = setupBrowser(t);
  const links = buildAppInstallLinks("atacadao", "ios");
  browser.location.assign = (url) => {
    if (url === links.openUrl) throw new Error("Unsupported URL scheme");
    navigations.push(url);
  };
  openAppWithStoreFallback(links, browser);
  t.mock.timers.runAll();
  assert.deepEqual(navigations, [links.storeUrl]);
});
