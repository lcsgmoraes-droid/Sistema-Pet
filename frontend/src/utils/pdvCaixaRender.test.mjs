import assert from "node:assert/strict";
import { after, test } from "node:test";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import react from "@vitejs/plugin-react";
import { createServer } from "vite";

const servidor = await createServer({
  root: fileURLToPath(new URL("../../", import.meta.url)),
  configFile: false,
  plugins: [react()],
  optimizeDeps: { noDiscovery: true },
  server: { middlewareMode: true, watch: null, ws: false },
});
after(() => servidor.close());
const { default: Banners } = await servidor.ssrLoadModule("/src/components/pdv/PDVInfoBanners.jsx");
const { default: Menu } = await servidor.ssrLoadModule("/src/components/MenuCaixa.jsx");
const { default: Acoes } = await servidor.ssrLoadModule(
  "/src/components/pdv/PDVAcoesFooterCard.jsx",
);
const { ModalSangria } = await servidor.ssrLoadModule("/src/components/ModaisCaixa.jsx");
const renderizar = (Componente, props) =>
  renderToStaticMarkup(React.createElement(Componente, props));

test("banner e menu não anunciam fechado nem oferecem abertura em consulta pendente/erro", () => {
  for (const statusConsultaCaixa of ["carregando", "erro"]) {
    const banner = renderizar(Banners, {
      statusConsultaCaixa,
      temCaixaAberto: false,
      vendaAtual: {},
    });
    const menu = renderizar(Menu, { statusConsultaCaixa, caixaAberto: null });
    assert.doesNotMatch(banner, /CAIXA FECHADO/);
    assert.doesNotMatch(menu, /Abrir Caixa/);
    if (statusConsultaCaixa === "erro") {
      assert.match(banner, /Tentar novamente/);
      assert.match(menu, /Verificar caixa/);
    }
  }
});

test("falha após confirmação de aberto conserva menu aberto e avisa que a consulta falhou", () => {
  const banner = renderizar(Banners, {
    statusConsultaCaixa: "erro",
    temCaixaAberto: true,
    vendaAtual: {},
  });
  const menu = renderizar(Menu, {
    statusConsultaCaixa: "erro",
    caixaAberto: { id: 9, numero_caixa: 3, status: "aberto" },
  });
  assert.match(banner, /último caixa confirmado continua aberto/);
  assert.doesNotMatch(banner, /CAIXA FECHADO/);
  assert.match(menu, /Caixa #3/);
  assert.doesNotMatch(menu, /Abrir Caixa/);
});

test("ausência confirmada pelo servidor mostra fechado e oferece abertura", () => {
  const banner = renderizar(Banners, {
    statusConsultaCaixa: "pronto",
    temCaixaAberto: false,
    vendaAtual: {},
  });
  const menu = renderizar(Menu, { statusConsultaCaixa: "pronto", caixaAberto: null });
  assert.match(banner, /CAIXA FECHADO/);
  assert.match(menu, /Abrir Caixa/);
});

test("ações continuam bloqueadas no estado desconhecido com instrução correta", () => {
  for (const statusConsultaCaixa of ["carregando", "erro"]) {
    const acoes = renderizar(Acoes, { itensCount: 1, statusConsultaCaixa, temCaixaAberto: false });
    assert.doesNotMatch(acoes, /Caixa fechado/);
    assert.equal((acoes.match(/disabled=""/g) || []).length, 2);
    assert.match(
      acoes,
      statusConsultaCaixa === "erro" ? /verificar o caixa/ : /Verificando o caixa/,
    );
  }
  const aberto = renderizar(Acoes, {
    itensCount: 1,
    statusConsultaCaixa: "erro",
    temCaixaAberto: true,
    statusVenda: "aberta",
  });
  assert.doesNotMatch(aberto, /disabled=""/);
});

test("sangria apresenta saldo pendente ou erro sem inventar zero e depois mostra o saldo recebido", () => {
  const props = { caixaId: 9, numeroCaixa: 3, saldoAtual: null };
  const pendente = renderizar(ModalSangria, { ...props, statusResumo: "carregando" });
  assert.match(pendente, /Consultando saldo/);
  assert.equal(pendente.match(/Em caixa:<\/strong>([^<]*)/)[1].trim(), "Consultando saldo...");
  const falha = renderizar(ModalSangria, { ...props, statusResumo: "erro" });
  assert.match(falha, /Saldo indisponível/);
  assert.match(falha, /Tentar novamente/);
  const carregado = renderizar(ModalSangria, {
    ...props,
    saldoAtual: 1234.5,
    statusResumo: "pronto",
  });
  assert.match(carregado, /1\.234,50/);
  assert.doesNotMatch(carregado, /Consultando saldo/);
});
