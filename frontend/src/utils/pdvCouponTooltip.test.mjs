import assert from "node:assert/strict";
import { test } from "node:test";

import { buildPdvCouponTooltip } from "./pdvCouponTooltip.js";

test("buildPdvCouponTooltip descreve campanha, valor, validade e regras do cupom", () => {
  const tooltip = buildPdvCouponTooltip({
    code: "CAMP-ABC123",
    nome_campanha: "Recompra Rapida (10 dias)",
    campaign_type: "quick_repurchase",
    coupon_type: "fixed",
    discount_value: 15,
    min_purchase_value: 80,
    valid_until: "2026-06-10T03:00:00Z",
    channel: "pdv",
    meta: {
      motivo: "Gerado apos venda finalizada",
      regras_resumo: "Pode ser usado apenas no PDV.",
    },
  });

  assert.match(tooltip, /Cupom CAMP-ABC123/);
  assert.match(tooltip, /Campanha: Recompra Rapida \(10 dias\)/);
  assert.match(tooltip, /Tipo: Recompra rapida/);
  assert.match(tooltip, /Beneficio: R\$ 15,00 de desconto/);
  assert.match(tooltip, /Compra minima: R\$ 80,00/);
  assert.match(tooltip, /Valido ate: 10\/06\/2026/);
  assert.match(tooltip, /Canal: PDV/);
  assert.match(tooltip, /Origem: Gerado apos venda finalizada/);
  assert.match(tooltip, /Regras: Pode ser usado apenas no PDV\./);
});

test("buildPdvCouponTooltip usa fallback claro para cupom manual sem campanha", () => {
  const tooltip = buildPdvCouponTooltip({
    code: "CORTESIA",
    coupon_type: "percent",
    discount_percent: 10,
    channel: "all",
  });

  assert.match(tooltip, /Campanha: Cupom manual/);
  assert.match(tooltip, /Beneficio: 10% de desconto/);
  assert.match(tooltip, /Canal: Todos os canais/);
});

test("buildPdvCouponTooltip explica regras vindas da configuracao da campanha", () => {
  const tooltip = buildPdvCouponTooltip({
    code: "CAMP-10DIAS",
    nome_campanha: "Recompra Rapida",
    campaign_type: "quick_repurchase",
    coupon_type: "percent",
    discount_percent: 5,
    channel: "pdv",
    campaign_params: {
      coupon_valid_days: 10,
      cooldown_days: 30,
      benefit_channels: ["loja_fisica", "app"],
    },
  });

  assert.match(tooltip, /Regras: Gerado apos uma compra finalizada/);
  assert.match(tooltip, /validade configurada de 10 dia\(s\)/);
  assert.match(tooltip, /novo cupom no maximo a cada 30 dia\(s\)/);
  assert.match(tooltip, /Canais de beneficio: Loja \/ PDV, App/);
});
