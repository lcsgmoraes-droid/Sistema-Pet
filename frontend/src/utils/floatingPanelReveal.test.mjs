import assert from "node:assert/strict";
import test from "node:test";

import {
  painelFlutuantePrecisaRevelar,
  revelarPainelFlutuante,
} from "./floatingPanelReveal.js";

test("painelFlutuantePrecisaRevelar detecta painel abaixo da area visivel", () => {
  assert.equal(
    painelFlutuantePrecisaRevelar(
      { top: 720, bottom: 940 },
      { viewportHeight: 800, margin: 24 },
    ),
    true,
  );
});

test("painelFlutuantePrecisaRevelar ignora painel ja visivel", () => {
  assert.equal(
    painelFlutuantePrecisaRevelar(
      { top: 240, bottom: 520 },
      { viewportHeight: 800, margin: 24 },
    ),
    false,
  );
});

test("revelarPainelFlutuante rola somente quando painel ficaria cortado", () => {
  let opcoesRecebidas = null;
  const painel = {
    getBoundingClientRect: () => ({ top: 720, bottom: 940 }),
    scrollIntoView: (opcoes) => {
      opcoesRecebidas = opcoes;
    },
  };

  assert.equal(
    revelarPainelFlutuante(painel, {
      behavior: "auto",
      margin: 24,
      viewportHeight: 800,
    }),
    true,
  );
  assert.deepEqual(opcoesRecebidas, {
    behavior: "auto",
    block: "nearest",
    inline: "nearest",
  });
});

test("revelarPainelFlutuante nao rola quando painel ja esta visivel", () => {
  let chamado = false;
  const painel = {
    getBoundingClientRect: () => ({ top: 240, bottom: 520 }),
    scrollIntoView: () => {
      chamado = true;
    },
  };

  assert.equal(
    revelarPainelFlutuante(painel, {
      behavior: "auto",
      margin: 24,
      viewportHeight: 800,
    }),
    false,
  );
  assert.equal(chamado, false);
});
