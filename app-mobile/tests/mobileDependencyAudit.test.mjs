import assert from "node:assert/strict";
import { test } from "node:test";

import { evaluateAudit } from "../scripts/audit-dependencies.mjs";

const IMAGE_SIZE_ADVISORIES = [
  {
    url: "https://github.com/advisories/GHSA-w3rx-r6r6-pgpr",
  },
  {
    url: "https://github.com/advisories/GHSA-5p2g-fcmc-qvqq",
  },
];

test("aceita somente os alertas sem correcao do image-size usado pelo Metro", () => {
  const result = evaluateAudit({
    vulnerabilities: {
      "image-size": { severity: "high", via: IMAGE_SIZE_ADVISORIES },
      metro: {
        severity: "high",
        via: ["image-size", "metro-config", "metro-transform-worker"],
      },
      "metro-config": { severity: "high", via: ["metro"] },
      "metro-transform-worker": { severity: "high", via: ["metro"] },
    },
  });

  assert.deepEqual(result.blocked, []);
  assert.deepEqual(
    result.ignored.map((item) => item.name),
    ["image-size", "metro", "metro-config", "metro-transform-worker"],
  );
});

test("bloqueia image-size se o codigo do aplicativo importar o parser", () => {
  const result = evaluateAudit(
    {
      vulnerabilities: {
        "image-size": { severity: "high", via: IMAGE_SIZE_ADVISORIES },
      },
    },
    { sourceImportsImageSize: true },
  );

  assert.deepEqual(result.ignored, []);
  assert.equal(result.blocked[0].name, "image-size");
});

test("continua bloqueando qualquer outro alerta moderado ou superior", () => {
  const result = evaluateAudit({
    vulnerabilities: {
      "outra-dependencia": {
        severity: "high",
        via: [
          {
            url: "https://github.com/advisories/GHSA-AAAA-BBBB-CCCC",
          },
        ],
      },
    },
  });

  assert.deepEqual(result.ignored, []);
  assert.equal(result.blocked[0].name, "outra-dependencia");
});
