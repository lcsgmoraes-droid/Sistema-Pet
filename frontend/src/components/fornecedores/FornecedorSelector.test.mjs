import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

test("fornecedor local busca código além dos primeiros 80 e preserva seleção de grupo", async () => {
  const grupos = [];
  const grupo = { id: 8, nome: "Grupo de teste", ativo: true };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./FornecedorSelector.jsx", import.meta.url)),
    {
      props: {
        fornecedores: Array.from({ length: 100 }, (_, i) => ({
          id: i + 1,
          codigo: `C${i}`,
          nome: `Fornecedor ${i}`,
        })),
        gruposFornecedores: [grupo],
        onSelectGrupo: (item) => grupos.push(item),
        searchRemote: false,
        allowCreate: false,
      },
      mocks: new Map([
        ["react-dom", { createPortal: (node) => node }],
        ["lucide-react", {}],
        [
          "../../api/clientes",
          {
            buscarClientes: async () => {
              throw new Error("Não deve consultar API neste modo");
            },
          },
        ],
        [
          "../clientes/PessoaFormularioModal",
          { __esModule: true, default: "PessoaFormularioModal" },
        ],
        ["../v2/BuscaPessoa/BuscaPessoa", { __esModule: true, default: "BuscaPessoa" }],
        ["../v2/BotaoInteracao/BotaoInteracao", { __esModule: true, default: "BotaoInteracao" }],
        ["../v2/BotaoCancelar/BotaoCancelar", { __esModule: true, default: "BotaoCancelar" }],
      ]),
      globals: { document: { body: {}, addEventListener() {}, removeEventListener() {} } },
    },
  );
  const campo = () => elements(harness.tree).find((node) => node.type === "BuscaPessoa");
  await harness.settle();
  await harness.act(() => campo().props.onChange("C99"));
  assert.equal(campo().props.suggestions[0].id, 100);
  await harness.act(() => campo().props.onChange("grupo teste"));
  await harness.act(() => campo().props.onSelect(campo().props.suggestions[0]));
  assert.equal(grupos[0], grupo);
});
