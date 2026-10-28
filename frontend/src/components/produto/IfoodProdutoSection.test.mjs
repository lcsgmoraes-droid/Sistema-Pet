import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const stub = (value) => ({ __esModule: true, default: value });
test("publicação recebe o rascunho atual dentro da seção canônica sem substituir campos em edição", async () => {
  const changes = [];
  const formData = {
    id: 6398,
    codigo: "018631.1",
    nome: "Produto fictício",
    anunciar_ifood: true,
    preco_venda: 100,
    preco_ifood: 120,
  };
  const imagens = [{ url: "/foto-fixture.webp", principal: true }];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./IfoodProdutoSection.jsx", import.meta.url)),
    {
      props: { formData, imagens, handleChange: (...args) => changes.push(args) },
      mocks: new Map([
        ["lucide-react", {}],
        [
          "../../api/ifood",
          {
            previewIfoodProduto() {
              throw Error("No request until debounce");
            },
          },
        ],
        ["../../hooks/useIfoodPromotionRefresh", stub(() => {})],
        ...[
          "BotaoInteracao",
          "BotaoLink",
          "InputCheckTexto",
          "InputMoeda",
          "InputRadio",
          "LinkPadrao",
        ].map((name) => [`../v2/${name}/${name}`, stub(name)]),
        ["./PromocaoFields", stub("PromocaoFields")],
        ["../ifood/IfoodPremissasOrigem", stub("IfoodPremissasOrigem")],
        ["../ifood/IfoodPublicacaoProduto", stub("IfoodPublicacaoProduto")],
      ]),
      globals: { AbortController, setTimeout: () => 1, clearTimeout() {} },
    },
  );
  let block = elements(harness.tree).find((el) => el.type === "IfoodPublicacaoProduto");
  assert.equal(block.props.productId, 6398);
  assert.equal(block.props.draft, formData);
  assert.equal(block.props.imagens, imagens);
  const edited = { ...formData, preco_ifood: 135, nome: "Rascunho mantido" };
  await harness.update({ formData: edited });
  block = elements(harness.tree).find((el) => el.type === "IfoodPublicacaoProduto");
  assert.equal(block.props.draft, edited);
  const price = elements(harness.tree).find(
    (el) => el.type === "InputMoeda" && el.props.id === "produto-preco-ifood",
  );
  assert.equal(price.props.value, 135);
  assert.equal(changes.length, 0);
});
