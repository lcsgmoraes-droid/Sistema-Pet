import assert from "node:assert/strict";
import test from "node:test";

import {
  intnfeCertificateAlertKey,
  markIntNFeCertificateAlert,
  shouldNotifyIntNFeCertificate,
} from "./intnfeCertificateAlert.mjs";

function memoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
}

test("mostra o alerta de vencimento uma vez por empresa e por dia", () => {
  const storage = memoryStorage();
  const morning = new Date(2026, 8, 11, 8);
  const afternoon = new Date(2026, 8, 11, 17);
  const nextDay = new Date(2026, 8, 12, 8);
  const status = { certificado_alerta: "O certificado vence em 20 dias." };

  assert.equal(shouldNotifyIntNFeCertificate(status, "tenant-a", storage, morning), true);
  markIntNFeCertificateAlert("tenant-a", storage, morning);
  assert.equal(shouldNotifyIntNFeCertificate(status, "tenant-a", storage, afternoon), false);
  assert.equal(shouldNotifyIntNFeCertificate(status, "tenant-b", storage, afternoon), true);
  assert.equal(shouldNotifyIntNFeCertificate(status, "tenant-a", storage, nextDay), true);
});

test("não cria aviso sem empresa ou sem alerta do backend", () => {
  const storage = memoryStorage();
  const now = new Date(2026, 8, 11, 8);

  assert.equal(intnfeCertificateAlertKey("", now), null);
  assert.equal(shouldNotifyIntNFeCertificate({}, "tenant-a", storage, now), false);
});
