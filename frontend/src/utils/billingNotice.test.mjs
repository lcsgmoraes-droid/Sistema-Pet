import assert from "node:assert/strict";
import { buildBillingNotice } from "./billingNotice.js";

assert.equal(buildBillingNotice(null), null);
assert.equal(buildBillingNotice({ status: "active", acesso_operacional_ativo: true }), null);
assert.equal(buildBillingNotice({ status: "trial", dias_restantes_trial: 20 }), null);

for (const etapa of ["lembrete", "atencao", "revisao_manual"]) {
  const aviso = buildBillingNotice({
    status: "past_due",
    acesso_operacional_ativo: true,
    avisos_cobranca: { etapa },
    tolerancia_atraso: { dias_restantes: 0 },
  });
  assert.equal(aviso.label, "Pagamento em atraso");
  assert.match(aviso.text, /acesso (continua|permanece) liberado/i);
  assert.doesNotMatch(aviso.text, /bloqueio|suspens|faltam/i);
}

const vencido = buildBillingNotice({
  status: "trial",
  status_efetivo: "expired",
  trial_expirado: true,
  acesso_operacional_ativo: true,
  acesso_completo_durante_trial: true,
});
assert.equal(vencido.label, "Período de teste encerrado");
assert.match(vencido.text, /acesso continua liberado/i);

const proximoDoFim = buildBillingNotice({ status: "trial", dias_restantes_trial: 1 });
assert.match(proximoDoFim.text, /Falta 1 dia para o fim do teste/);
assert.match(proximoDoFim.text, /acesso continuará liberado/i);

for (const assinatura of [
  { status: "trial", dias_restantes_trial: 1 },
  { status: "trial", dias_restantes_trial: 0, trial_expirado: true },
  { status: "trial", status_efetivo: "expired", trial_expirado: true },
  { status: "expired" },
]) {
  assert.equal(buildBillingNotice({ ...assinatura, acesso_completo_manual: true }), null);
  assert.notEqual(buildBillingNotice({ ...assinatura, acesso_completo_manual: false }), null);
}

for (const status of ["past_due", "pending", "blocked", "refunded", "canceled"]) {
  for (const etapa of ["lembrete", "atencao", "revisao_manual"]) {
    const assinatura = {
      status,
      trial_expirado: true,
      acesso_operacional_ativo: true,
      avisos_cobranca: { etapa },
    };
    assert.deepEqual(
      buildBillingNotice({ ...assinatura, acesso_completo_manual: true }),
      buildBillingNotice({ ...assinatura, trial_expirado: false }),
      "A liberação manual deve preservar o aviso financeiro",
    );
  }
}

for (const status of ["pending", "blocked", "refunded", "canceled"]) {
  const aviso = buildBillingNotice({ status, acesso_operacional_ativo: true });
  assert.match(aviso.text, /acesso continua liberado/i);
  assert.notEqual(aviso.icon, "lock");
}

const suspenso = buildBillingNotice({
  status: "active",
  acesso_operacional_ativo: false,
  acesso_completo_durante_trial: true,
});
assert.equal(suspenso.label, "Acesso suspenso pela administração");
assert.equal(suspenso.icon, "lock");
assert.doesNotMatch(suspenso.text, /acesso continua liberado/i);
assert.deepEqual(
  buildBillingNotice({
    status: "trial",
    trial_expirado: true,
    acesso_operacional_ativo: false,
    acesso_completo_manual: true,
  }),
  suspenso,
);

console.log("Billing notices preserve financial facts and respect manual access and suspension");
