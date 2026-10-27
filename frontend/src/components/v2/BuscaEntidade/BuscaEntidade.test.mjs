import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
} from "../../../../scripts/helpers/reactControllerHarness.mjs";

function ambiente(extra = {}) {
  const selecionados = [];
  const teclas = [];
  const h = createControllerHarness(
    fileURLToPath(new URL("./BuscaEntidade.jsx", import.meta.url)),
    {
      mocks: new Map([
        ["../InputTexto/InputTexto", { __esModule: true, default: "InputTexto" }],
        ["../../../hooks/useRevealFloatingPanel", { __esModule: true, default: () => {} }],
        ["lucide-react", { Search: "Search" }],
      ]),
      props: {
        tipo: "pessoa",
        value: "2292",
        showSuggestions: true,
        suggestions: [
          { id: 1, codigo: "12292", nome: "Ana" },
          { id: 2, codigo: "2292", nome: "Fernanda" },
        ],
        onSelect: (pessoa) => selecionados.push(pessoa.id),
        onKeyDown: (evento) => teclas.push(evento.key),
        renderDefault: (pessoa) => pessoa.nome,
        ...extra,
      },
    },
  );
  const campo = () => elements(h.tree).find((el) => el.type === "InputTexto");
  const tecla = async (key) => h.act(() => campo().props.onKeyDown({ key, preventDefault() {} }));
  return { h, campo, tecla, selecionados, teclas };
}

test("setas escolhem a sugestão relevante; Enter sem setas preserva o scanner do consumidor", async () => {
  const a = ambiente();
  await a.h.settle();
  await a.tecla("Enter");
  assert.deepEqual(a.teclas, ["Enter"]);
  assert.deepEqual(a.selecionados, []);
  await a.tecla("ArrowDown");
  await a.tecla("Enter");
  assert.deepEqual(a.selecionados, [2]);
  assert.equal(a.campo().props.inputProps["aria-expanded"], false);
});

test("Escape fecha resultados e campo preserva obrigatório, erro e ajuda V2", async () => {
  const a = ambiente({ required: true, label: "Pessoa", error: "Selecione", help: "Use o código" });
  await a.h.settle();
  assert.equal(a.campo().props.required, true);
  assert.equal(a.campo().props.error, "Selecione");
  assert.equal(a.campo().props.help, "Use o código");
  await a.tecla("Escape");
  assert.equal(a.campo().props.inputProps["aria-expanded"], false);
});

test("resposta assíncrona menor preserva índice válido ao confirmar pelo teclado", async () => {
  const a = ambiente();
  await a.h.settle();
  await a.tecla("ArrowDown");
  await a.tecla("ArrowDown");
  await a.h.update({ suggestions: [{ id: 9, codigo: "2292", nome: "Nova sugestão" }] });
  await a.tecla("Enter");
  assert.deepEqual(a.selecionados, [9]);
});
