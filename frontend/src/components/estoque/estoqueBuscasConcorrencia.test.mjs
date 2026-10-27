import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

for (const clinico of [false, true]) {
  test(`${clinico ? "fracionamento" : "granel"} cancela busca antiga e preserva seleção ao chegar fora de ordem`, async () => {
    const timers = new Map();
    const chamadas = [];
    let sequencia = 0;
    const timerApi = {
      setTimeout: (fn) => {
        timers.set(++sequencia, fn);
        return sequencia;
      },
      clearTimeout: (id) => timers.delete(id),
    };
    const api = {
      get: (url, config) => {
        if (url.endsWith("/produtos") && config?.params?.busca)
          return new Promise((resolve) => chamadas.push({ url, config, resolve }));
        return Promise.resolve({
          data:
            url.endsWith("/produtos") || url.includes("/vinculos/")
              ? []
              : { vinculos: [], lotes: [] },
        });
      },
    };
    const harness = createControllerHarness(
      fileURLToPath(
        new URL(
          clinico
            ? "./useMovimentacoesProdutoFracionamento.js"
            : "./useMovimentacoesProdutoGranel.js",
          import.meta.url,
        ),
      ),
      {
        exportName: clinico
          ? "useMovimentacoesProdutoFracionamento"
          : "useMovimentacoesProdutoGranel",
        props: {
          id: 123,
          produto: { tipo_produto: "SIMPLES", peso_embalagem: 1, preco_custo: 2, preco_venda: 4 },
          carregarDados() {},
        },
        mocks: new Map([
          [
            "react-hot-toast",
            {
              __esModule: true,
              default: {
                error(message) {
                  throw new Error(message);
                },
                success() {},
              },
            },
          ],
          ["../../api", { __esModule: true, default: api }],
          ["../../utils/formatters", { formatMoneyBRL: String }],
          [
            "./movimentacoesProdutoUtils",
            {
              parseNumeroInputMovimentacao: Number,
              formatarQuantidadeMovimentacao: String,
              extrairMensagemErroApiMovimentacao: (_error, message) => message,
            },
          ],
          [
            "./granelPrecoUtils",
            { ALTERAR_PRECO_GRANEL_PADRAO: true, montarCamposAtualizacaoPrecoGranel: () => ({}) },
          ],
          [
            "./fracionamentoClinicoUtils",
            {
              calcularQuantidadeDestinoFracionamento: () => 0,
              montarPayloadFracionamentoClinico: () => ({}),
              resolverConfiguracaoVinculoFracionamento: () => null,
            },
          ],
          ["../../services/corepetDialog", {}],
        ]),
        globals: { ...timerApi, window: timerApi, AbortController },
      },
    );
    await harness.act(() => (clinico ? harness.tree.onAbrir() : harness.tree.abrirModalGranel()));
    const setBusca = (termo) =>
      clinico ? harness.tree.setBusca(termo) : harness.tree.setBuscaGranel(termo);
    const lista = () => (clinico ? harness.tree.produtosDisponiveis : harness.tree.granelProdutos);
    const disparar = async () => {
      const [id, fn] = [...timers].at(-1);
      timers.delete(id);
      fn();
      await harness.settle();
    };
    await harness.act(() => setBusca("primeira"));
    await disparar();
    await harness.act(() => setBusca("segunda"));
    assert.equal(chamadas[0].config.signal.aborted, true);
    await disparar();
    assert.equal(
      chamadas[1].url,
      clinico ? "/estoque/fracionamento-clinico/produtos" : "/estoque/granel/produtos",
    );
    if (clinico) assert.equal(chamadas[1].config.params.produto_origem_id, 123);
    chamadas[1].resolve({ data: [{ id: 22, codigo: "B", nome: "Segunda" }] });
    await harness.settle();
    await harness.act(() =>
      clinico ? harness.tree.onSelecionarProduto(22) : harness.tree.handleSelecionarGranel(22, 4),
    );
    chamadas[0].resolve({ data: [{ id: 11, codigo: "A", nome: "Primeira" }] });
    await harness.settle();
    assert.equal(lista()[0].id, 22);
    assert.equal(clinico ? harness.tree.produtoDestinoId : harness.tree.granelSelecionadoId, "22");
    await harness.act(() => setBusca("terceira"));
    await disparar();
    await harness.act(() =>
      clinico ? harness.tree.fechar() : harness.tree.setShowGranelModal(false),
    );
    assert.equal(chamadas[2].config.signal.aborted, true);
    chamadas[2].resolve({ data: [{ id: 33, nome: "Resposta após fechar" }] });
    await harness.settle();
    assert.equal(
      lista().some((produto) => produto.id === 33),
      false,
    );
    harness.unmount();
  });
}
