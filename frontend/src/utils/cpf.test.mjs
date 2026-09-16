import assert from "node:assert/strict";

import { formatCpf, normalizeCpf, validarCpf } from "./cpf.js";

assert.equal(normalizeCpf("529.982.247-25"), "52998224725");
assert.equal(formatCpf("52998224725"), "529.982.247-25");
assert.equal(validarCpf("529.982.247-25"), true);
assert.equal(validarCpf("111.111.111-11"), false);
assert.equal(validarCpf("529.982.247-24"), false);

console.log("CPF utility checks passed.");
