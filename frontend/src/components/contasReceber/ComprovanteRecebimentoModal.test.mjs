import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const componentPath = fileURLToPath(new URL("./ComprovanteRecebimentoModal.jsx", import.meta.url));
const comprovante = {
  id: 501,
  contaId: 101,
  clienteNome: "Ana",
  descricao: "Crediário parcela 1",
  data: "2026-10-23",
  formaPagamento: "Pix",
  valor: 30,
  saldoRestante: 70,
};

function preparar(props = {}) {
  let impressoes = 0;
  let fechamentos = 0;
  const harness = createControllerHarness(componentPath, {
    props: {
      onClose: () => {
        fechamentos += 1;
      },
      ...props,
    },
    globals: {
      globalThis: {
        print: () => {
          impressoes += 1;
        },
      },
    },
    mocks: new Map([
      ["lucide-react", { Printer: "Printer" }],
      ["react-dom", { createPortal: (conteudo) => conteudo }],
      ...["BotaoCancelar", "BotaoInteracao", "ModalPadrao"].map((name) => [
        `../v2/${name}/${name}`,
        { __esModule: true, default: name },
      ]),
    ]),
  });
  return { harness, impressoes: () => impressoes, fechamentos: () => fechamentos };
}

function modal(harness) {
  return elements(harness.tree).find((node) => node.type === "ModalPadrao");
}

function botao(harness, texto) {
  const match = elements(modal(harness).props.rodape).find((node) => elementText(node) === texto);
  assert.ok(match, `Botão ${texto} disponível`);
  return match;
}

test("sem recebimentos confirmados não abre modal nem dispara impressão", async () => {
  const { harness, impressoes } = preparar();
  await harness.settle();
  assert.equal(harness.tree, null);
  assert.equal(impressoes(), 0);
});

test("após o pagamento só imprime quando o usuário escolhe Sim, imprimir", async () => {
  const { harness, impressoes, fechamentos } = preparar({
    comprovantes: [comprovante],
    perguntarImpressao: true,
  });
  await harness.settle();
  assert.equal(modal(harness).props.titulo, "Deseja imprimir o comprovante?");
  assert.match(elementText(harness.tree), /Pagamento registrado com sucesso/);
  assert.equal(impressoes(), 0);
  await harness.act(() => botao(harness, "Sim, imprimir").props.onClick());
  assert.equal(impressoes(), 1);
  assert.equal(fechamentos(), 0);
});

test("Agora não fecha a pergunta sem imprimir", async () => {
  const { harness, impressoes, fechamentos } = preparar({
    comprovantes: [comprovante],
    perguntarImpressao: true,
  });
  await harness.act(() => botao(harness, "Agora não").props.onClick());
  assert.equal(impressoes(), 0);
  assert.equal(fechamentos(), 1);
});

test("fechar pelo cabeçalho dispensa a impressão sem outro efeito", async () => {
  const { harness, impressoes, fechamentos } = preparar({
    comprovantes: [comprovante],
    perguntarImpressao: true,
  });
  await harness.act(() => modal(harness).props.onFechar());
  assert.equal(impressoes(), 0);
  assert.equal(fechamentos(), 1);
});

test("histórico continua permitindo imprimir um recebimento já registrado", async () => {
  const { harness, impressoes } = preparar({ comprovantes: [comprovante] });
  assert.equal(modal(harness).props.titulo, "Comprovante de recebimento");
  assert.doesNotMatch(elementText(harness.tree), /Pagamento registrado com sucesso/);
  assert.equal(impressoes(), 0);
  await harness.act(() => botao(harness, "Imprimir comprovante").props.onClick());
  assert.equal(impressoes(), 1);
  assert.ok(botao(harness, "Fechar"));
});

test("lote apresenta e imprime um recibo por cliente com seus próprios valores", async () => {
  const outroComprovante = {
    ...comprovante,
    id: 502,
    contaId: 202,
    clienteNome: "Bruno",
    descricao: "Crediário parcela 2",
    valor: 75,
    saldoRestante: 0,
  };
  const { harness, impressoes } = preparar({
    comprovantes: [comprovante, outroComprovante],
    perguntarImpressao: true,
  });
  assert.equal(modal(harness).props.titulo, "Deseja imprimir os comprovantes?");
  const artigos = elements(harness.tree).filter((node) => node.type === "article");
  assert.equal(artigos.length, 2);
  assert.match(elementText(artigos[0]), /Ana/);
  assert.match(elementText(artigos[1]), /Bruno/);
  const area = elements(harness.tree).find((node) => typeof node.type === "function");
  assert.ok(area, "Área de impressão disponível");
  const recibos = elements(area.type(area.props)).filter((node) => node.type === "pre");
  assert.equal(recibos.length, 2);
  assert.match(elementText(recibos[0]), /CR-101-R-501/);
  assert.match(elementText(recibos[0]), /Cliente: Ana/);
  assert.match(elementText(recibos[0]), /R\$\s*30,00/);
  assert.match(elementText(recibos[0]), /Saldo atual da conta: R\$\s*70,00/);
  assert.match(elementText(recibos[1]), /CR-202-R-502/);
  assert.match(elementText(recibos[1]), /Cliente: Bruno/);
  assert.match(elementText(recibos[1]), /R\$\s*75,00/);
  assert.match(elementText(recibos[1]), /Saldo atual da conta: R\$\s*0,00/);
  assert.equal(impressoes(), 0);
  await harness.act(() => botao(harness, "Sim, imprimir").props.onClick());
  assert.equal(impressoes(), 1);
});
