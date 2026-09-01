import assert from "node:assert/strict";
import test from "node:test";
import {
  contarPorPrazo,
  filtrarLembretes,
  pertenceAoPrazo,
  whatsappUrl,
} from "./lembretesUtils.js";

const reminders = [-3, 0, 1, 2, 3, 7, 8, 30, 31].map((dias_restantes, index) => ({
  cliente_nome: index === 3 ? "João" : `Cliente ${index}`,
  dias_restantes,
  pet_nome: "Thor",
  produto_nome: index === 3 ? "Ração Premium" : "Produto",
  tipo_lembrete: index === 3 ? "racao" : "recorrencia",
}));

test("faixas de prazo são exclusivas", () => {
  const counts = contarPorPrazo(reminders);
  assert.deepEqual(counts, {
    todos: 9,
    atrasados: 1,
    hoje: 1,
    "1-2": 2,
    "3-7": 2,
    "8-30": 2,
    "+30": 1,
  });
  assert.equal(pertenceAoPrazo(-1, "3-7"), false);
  assert.equal(pertenceAoPrazo(7, "3-7"), true);
  assert.equal(pertenceAoPrazo(8, "3-7"), false);
});

test("busca e tipo podem ser combinados", () => {
  const result = filtrarLembretes(reminders, {
    busca: "joao racao",
    prazo: "1-2",
    tipo: "racao",
  });
  assert.equal(result.length, 1);
  assert.equal(result[0].cliente_nome, "João");
});

test("link do WhatsApp normaliza telefone brasileiro e codifica a mensagem", () => {
  assert.equal(
    whatsappUrl("(11) 99999-0000", "Olá, tudo bem?"),
    "https://wa.me/5511999990000?text=Ol%C3%A1%2C%20tudo%20bem%3F",
  );
  assert.equal(whatsappUrl("", "mensagem"), null);
});
