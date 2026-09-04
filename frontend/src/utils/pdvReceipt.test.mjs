import assert from "node:assert/strict";
import test from "node:test";

import {
  ehVendaCrediario,
  montarConteudoCupom,
  montarCupomCrediario,
  montarCupomVenda,
} from "./pdvReceipt.js";

const vendaBase = {
  id: 5325,
  numero_venda: "VEN-5325",
  data_venda: "2026-09-03T12:03:50-03:00",
  subtotal: 390,
  desconto_valor: 0,
  total: 390,
  cliente: {
    nome: "Cliente de Teste",
    telefone: "(18) 99999-0000",
    endereco: "Rua Exemplo",
    numero: "100",
    bairro: "Centro",
    cidade: "Andradina",
    uf: "SP",
  },
  itens: [
    {
      produto_nome: "Ração Premium 10 kg",
      quantidade: 1,
      preco_unitario: 390,
      subtotal: 390,
    },
  ],
};

const empresa = {
  cupom_cabecalho: "Cuidando de quem faz parte da família",
  cupom_mensagem_final: "Agradecemos a preferência. Até a próxima!",
  nome_fantasia: "Pet Shop Exemplo",
  razao_social: "Pet Shop Exemplo Ltda",
  cnpj: "12.345.678/0001-90",
  endereco: "Rua Comercial",
  numero: "1374",
  bairro: "Centro",
  cidade: "Andradina",
  uf: "SP",
  cep: "16900-010",
  telefone: "(18) 3723-0000",
  email: "contato@exemplo.test",
};

test("recibo do PDV usa cadastro real e textos personalizados da empresa", () => {
  const recibo = montarCupomVenda(
    {
      ...vendaBase,
      pagamentos: [{ forma_pagamento: "Pix", valor: 390 }],
    },
    empresa,
  );

  assert.match(recibo, /Cuidando de quem faz parte da familia/);
  assert.match(recibo, /Pet Shop Exemplo/);
  assert.match(recibo, /Pet Shop Exemplo Ltda/);
  assert.match(recibo, /CNPJ: 12\.345\.678\/0001-90/);
  assert.match(recibo, /Rua Comercial, 1374, Centro/);
  assert.match(recibo, /Contato: \(18\) 3723-0000/);
  assert.match(recibo, /Agradecemos a preferencia/);
  assert.match(recibo, /DOCUMENTO NAO FISCAL/);
  assert.doesNotMatch(recibo, /PET SHOP PRO|Central de Gestao/);
});

test("configuracoes opcionais vazias usam fallback sensato", () => {
  const recibo = montarCupomVenda(vendaBase, {});

  assert.match(recibo, /SISTEMA PET/);
  assert.match(recibo, /Obrigado pela preferencia!/);
  assert.match(recibo, /Volte sempre!/);
});

test("crediario imprime cupom e duas vias da nota promissoria em folhas separadas", () => {
  const vendaCrediario = {
    ...vendaBase,
    pagamentos: [
      {
        forma_pagamento: "Crediário",
        forma_pagamento_tipo: "crediario",
        valor: 390,
        numero_parcelas: 3,
        data_recebimento_prevista: "2027-01-31",
        intervalo_crediario: "mensal",
      },
    ],
  };
  const comprovante = montarCupomCrediario(vendaCrediario, empresa);

  assert.equal(ehVendaCrediario(vendaCrediario), true);
  assert.match(comprovante, /RECIBO DO PDV/);
  assert.match(comprovante, /VIA DO ESTABELECIMENTO/);
  assert.match(comprovante, /VIA DO CLIENTE/);
  assert.equal((comprovante.match(/NOTA PROMISSORIA/g) || []).length, 2);
  assert.equal((comprovante.match(/ASSINATURA DO EMITENTE/g) || []).length, 2);
  assert.equal((comprovante.match(/\f/g) || []).length, 2);
  assert.match(comprovante, /1\/3 31\/01\/2027/);
  assert.match(comprovante, /2\/3 28\/02\/2027/);
  assert.match(comprovante, /3\/3 31\/03\/2027/);
  assert.match(comprovante, /R\$ 130,00/);
  assert.match(comprovante, /trezentos e noventa reais/);
  assert.doesNotMatch(comprovante, /CORTE AQUI/);
  assert.equal(montarConteudoCupom(vendaCrediario, empresa), comprovante);
});

test("venda comum continua gerando apenas o recibo simples", () => {
  const recibo = montarConteudoCupom(
    { ...vendaBase, pagamentos: [{ forma_pagamento: "Dinheiro", valor: 390 }] },
    empresa,
  );

  assert.equal(ehVendaCrediario({ pagamentos: [{ forma_pagamento: "Dinheiro" }] }), false);
  assert.match(recibo, /RECIBO DO PDV/);
  assert.doesNotMatch(recibo, /VIA DO ESTABELECIMENTO|ASSINATURA DO CLIENTE/);
});
