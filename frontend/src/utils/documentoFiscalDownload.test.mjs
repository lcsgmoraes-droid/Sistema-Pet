import assert from "node:assert/strict";
import test from "node:test";

import { metadadosDownloadDanfe } from "./documentoFiscalDownload.mjs";

test("salva o DANFE termico da NFC-e como HTML", () => {
  assert.deepEqual(
    metadadosDownloadDanfe({ headers: { "content-type": "text/html; charset=utf-8" } }, 529),
    { nome: "danfe_529.html", tipo: "text/html;charset=utf-8" },
  );
});

test("mantem o DANFE da NF-e como PDF", () => {
  assert.deepEqual(metadadosDownloadDanfe({ headers: { get: () => "application/pdf" } }, 1630), {
    nome: "danfe_1630.pdf",
    tipo: "application/pdf",
  });
});
