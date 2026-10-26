import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const caminho = fileURLToPath(new URL("./AnaliseProdutosTabela.jsx", import.meta.url));
const mocks = new Map([
  ["lucide-react", { ChevronDown: "expandir", ChevronUp: "recolher" }],
  ["../../components/v2/BotaoInteracao/BotaoInteracao", { default: "botao", __esModule: true }],
  ["../../components/v2/InputCombobox/InputCombobox", { default: "ordenacao", __esModule: true }],
]);

const produto = {
  produto_id: 1,
  produto_nome: "Ração Premium",
  quantidade: 1250.5,
  faturamento: 17555.25,
  lucro_estimado: 1500,
  margem_estimada_pct: 8.55,
  estoque_atual: 30,
  vendedores: [
    {
      vendedor_id: 11,
      vendedor_nome: "Ana",
      quantidade: 1000,
      faturamento: 15000,
      participacao_faturamento_pct: 85.44,
    },
    {
      vendedor_id: null,
      vendedor_nome: "Sem vendedor informado",
      quantidade: 250.5,
      faturamento: 2555.25,
      participacao_faturamento_pct: 14.56,
    },
  ],
};

function montarLinha(item = produto) {
  return createControllerHarness(caminho, {
    mocks,
    props: { item },
    // Execute the actual child obtained from the table, with isolated hooks per product.
    invoke(Tabela, props) {
      const linha = elements(Tabela({ produtos: [props.item] })).find(
        (node) => typeof node.type === "function" && node.props?.item,
      );
      return linha.type(linha.props);
    },
  });
}

function botao(harness) {
  return elements(harness.tree).find((node) => node.type === "botao");
}

test("produto começa recolhido e expande vendedores com valores brasileiros e participação", async () => {
  const linha = montarLinha();
  assert.equal(botao(linha).props["aria-expanded"], false);
  assert.doesNotMatch(elementText(linha.tree), /Ana|Sem vendedor informado|Vendas por vendedor/);
  assert.match(elementText(linha.tree), /1\.250,5/);
  assert.match(elementText(linha.tree), /17\.555,25/);

  await linha.act(() => botao(linha).props.onClick());
  assert.equal(botao(linha).props["aria-expanded"], true);
  const regiao = elements(linha.tree).find((node) => node.props?.role === "region");
  assert.equal(regiao.props.id, botao(linha).props["aria-controls"]);
  assert.equal(regiao.props["aria-label"], "Vendedores de Ração Premium");
  const texto = elementText(regiao);
  for (const esperado of [
    "Ana",
    "Sem vendedor informado",
    "1.000",
    "15.000,00",
    "2.555,25",
    "85,44%",
    "14,56%",
  ]) {
    assert.ok(texto.includes(esperado), `Detalhamento deve incluir ${esperado}`);
  }

  await linha.act(() => botao(linha).props.onClick());
  assert.equal(botao(linha).props["aria-expanded"], false);
  assert.doesNotMatch(elementText(linha.tree), /Ana|Vendas por vendedor/);
});

test("expandir ou recolher um produto preserva a expansão do outro", async () => {
  const primeira = montarLinha();
  const segunda = montarLinha({ ...produto, produto_id: 2, produto_nome: "Petisco" });
  await primeira.act(() => botao(primeira).props.onClick());
  assert.equal(botao(primeira).props["aria-expanded"], true);
  assert.equal(botao(segunda).props["aria-expanded"], false);
  await segunda.act(() => botao(segunda).props.onClick());
  await primeira.act(() => botao(primeira).props.onClick());
  assert.equal(botao(primeira).props["aria-expanded"], false);
  assert.equal(botao(segunda).props["aria-expanded"], true);
});

test("detalhamento ausente não inventa vendedor nem atribui total a alguém", async () => {
  for (const vendedores of [undefined, null, []]) {
    const linha = montarLinha({ ...produto, vendedores });
    await linha.act(() => botao(linha).props.onClick());
    const regiao = elements(linha.tree).find((node) => node.props?.role === "region");
    assert.match(elementText(regiao), /Detalhamento de vendedores indisponível/);
    assert.doesNotMatch(elementText(regiao), /Sem vendedor informado|17\.555,25/);
  }
});

test("ordenação muda os produtos sem perder vendedores nem alterar a lista original", async () => {
  const segundo = {
    ...produto,
    produto_id: 2,
    produto_nome: "Petisco",
    quantidade: 2000,
    faturamento: 10,
  };
  const produtos = [segundo, produto];
  const tabela = createControllerHarness(caminho, { mocks, props: { produtos } });
  const linhas = () => elements(tabela.tree).filter((node) => node.props?.item);
  assert.deepEqual(
    linhas().map((node) => node.props.item.produto_id),
    [1, 2],
  );
  const seletor = elements(tabela.tree).find((node) => node.type === "ordenacao");
  await tabela.act(() => seletor.props.onChange("quantidade"));
  assert.deepEqual(
    linhas().map((node) => node.props.item.produto_id),
    [2, 1],
  );
  assert.strictEqual(linhas()[0].props.item.vendedores, segundo.vendedores);
  assert.strictEqual(linhas()[1].props.item.vendedores, produto.vendedores);
  assert.deepEqual(
    produtos.map((item) => item.produto_id),
    [2, 1],
  );
  assert.deepEqual(
    linhas().map((node) => node.key),
    [2, 1],
  );
});
