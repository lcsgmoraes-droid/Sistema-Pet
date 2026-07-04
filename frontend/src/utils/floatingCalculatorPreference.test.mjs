import assert from "node:assert/strict";
import test from "node:test";

import {
  FLOATING_CALCULATOR_ENABLED_KEY,
  FLOATING_CALCULATOR_PREF_EVENT,
  isFloatingCalculatorEnabled,
  setFloatingCalculatorEnabled,
} from "./floatingCalculatorPreference.js";

function criarStorageFake(valorInicial = new Map()) {
  const valores = new Map(valorInicial);

  return {
    getItem: (chave) => (valores.has(chave) ? valores.get(chave) : null),
    setItem: (chave, valor) => {
      valores.set(chave, valor);
    },
  };
}

test("calculadora flutuante fica desligada por padrao", () => {
  assert.equal(isFloatingCalculatorEnabled(criarStorageFake()), false);
});

test("calculadora flutuante so fica ativa quando preferencia salva for true", () => {
  assert.equal(
    isFloatingCalculatorEnabled(criarStorageFake([[FLOATING_CALCULATOR_ENABLED_KEY, "true"]])),
    true,
  );
  assert.equal(
    isFloatingCalculatorEnabled(criarStorageFake([[FLOATING_CALCULATOR_ENABLED_KEY, "false"]])),
    false,
  );
});

test("setFloatingCalculatorEnabled salva preferencia e avisa a tela atual", () => {
  const storage = criarStorageFake();
  const eventos = [];
  const eventTarget = {
    dispatchEvent: (evento) => {
      eventos.push(evento);
    },
  };

  setFloatingCalculatorEnabled(true, { storage, eventTarget });

  assert.equal(storage.getItem(FLOATING_CALCULATOR_ENABLED_KEY), "true");
  assert.equal(eventos[0].type, FLOATING_CALCULATOR_PREF_EVENT);
  assert.deepEqual(eventos[0].detail, { enabled: true });

  setFloatingCalculatorEnabled(false, { storage, eventTarget });

  assert.equal(storage.getItem(FLOATING_CALCULATOR_ENABLED_KEY), "false");
  assert.deepEqual(eventos[1].detail, { enabled: false });
});

test("preferencia nao quebra quando localStorage do navegador estiver indisponivel", () => {
  const windowOriginal = globalThis.window;

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {},
  });
  Object.defineProperty(globalThis.window, "localStorage", {
    configurable: true,
    get() {
      throw new Error("localStorage bloqueado");
    },
  });

  try {
    assert.equal(isFloatingCalculatorEnabled(), false);
    assert.equal(setFloatingCalculatorEnabled(true), true);
  } finally {
    if (windowOriginal === undefined) {
      delete globalThis.window;
    } else {
      Object.defineProperty(globalThis, "window", {
        configurable: true,
        value: windowOriginal,
      });
    }
  }
});
