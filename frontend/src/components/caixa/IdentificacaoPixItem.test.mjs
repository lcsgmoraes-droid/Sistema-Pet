import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const item = (estado = "nao_conferido", extra = {}) => ({
  id: 42,
  assinatura: "a".repeat(64),
  identificacao_pix: {
    estado,
    registro_id: estado === "nao_conferido" ? null : 9,
    justificativa: "Registro anterior",
    ...extra,
  },
});
function preparar({ registro = item(), salvar = async () => true, props = {} } = {}) {
  const gravacoes = [];
  const nomes = [
    "BotaoCancelar",
    "BotaoInteracao",
    "BotaoSalva",
    "InputCheckbox",
    "InputTextoLongo",
  ];
  const mocks = new Map(
    nomes.map((nome) => [`../v2/${nome}/${nome}`, { __esModule: true, default: nome }]),
  );
  mocks.set("lucide-react", {
    AlertTriangle: "AlertTriangle",
    CheckCircle2: "CheckCircle2",
    History: "History",
  });
  const h = createControllerHarness(
    fileURLToPath(new URL("./IdentificacaoPixItem.jsx", import.meta.url)),
    {
      mocks,
      props: {
        item: registro,
        onSalvar: (...args) => {
          gravacoes.push(args);
          return salvar(...args);
        },
        ...props,
      },
    },
  );
  const encontrar = (tipo) => elements(h.tree).find((el) => el.type === tipo);
  const botao = (texto) =>
    elements(h.tree).find((el) => elementText(el) === texto && el.type === "BotaoInteracao");
  const selecionar = (estado) =>
    h.act(() =>
      estado === "identificado"
        ? encontrar("InputCheckbox").props.onChange({ target: { checked: true } })
        : botao("Não identificado").props.onClick(),
    );
  const escrever = (motivo) => h.act(() => encontrar("InputTextoLongo").props.onChange(motivo));
  const confirmar = () => h.act(() => encontrar("BotaoSalva").props.onClick());
  return { h, gravacoes, encontrar, botao, selecionar, escrever, confirmar };
}

test("somente pagamentos elegiveis exibem controle; legado nao conferido nao gera alerta nem POST", async () => {
  for (const registro of [
    null,
    { id: 42 },
    { ...item(), assinatura: "invalida" },
    { ...item(), id: 0 },
  ]) {
    assert.equal(preparar({ registro }).h.tree, null);
  }
  const c = preparar();
  assert.match(elementText(c.h.tree), /Pix ainda não conferido/);
  assert.doesNotMatch(elementText(c.h.tree), /Pendência nos Alertas/);
  assert.equal(c.encontrar("InputCheckbox").props.checked, false);
  assert.equal(c.gravacoes.length, 0);
});

test("toda identificacao exige motivo e confirmacao, sem marcar ou colorir antes do servidor", async () => {
  for (const estado of ["identificado", "nao_identificado"]) {
    const c = preparar();
    await c.selecionar(estado);
    assert.equal(c.gravacoes.length, 0);
    assert.equal(c.encontrar("InputTextoLongo").props.required, true);
    assert.match(c.h.tree.props.className, /border-slate-200/);
    assert.equal(c.encontrar("InputCheckbox").props.checked, false);
    await c.confirmar();
    assert.equal(c.gravacoes.length, 0);
    assert.match(c.encontrar("InputTextoLongo").props.error, /Informe o motivo/);
    await c.escrever("  Conferido no extrato do banco.  ");
    await c.confirmar();
    assert.equal(c.gravacoes.length, 1);
    assert.equal(c.gravacoes[0][1], estado);
    assert.equal(c.gravacoes[0][2], "Conferido no extrato do banco.");
    assert.equal(c.encontrar("InputTextoLongo"), undefined);
    assert.match(c.h.tree.props.className, /border-slate-200/);
  }
});

test("Pix nao identificado e ambar, nao bloqueia caixa e permite identificacao posterior com motivo", async () => {
  const c = preparar({
    registro: item("nao_identificado", {
      usuario_nome: "Lucas",
      data: "2026-10-22T10:00:00-03:00",
    }),
  });
  assert.match(c.h.tree.props.className, /border-amber-300/);
  assert.match(elementText(c.h.tree), /Não impede o fechamento do caixa/);
  assert.equal(c.encontrar("InputCheckbox").props.disabled, false);
  await c.selecionar("identificado");
  await c.escrever("Cliente enviou comprovante e confirmei o crédito.");
  await c.confirmar();
  await c.h.update({
    item: item("identificado", { registro_id: 10, justificativa: "Confirmado" }),
  });
  assert.match(c.h.tree.props.className, /border-emerald-300/);
  assert.equal(c.encontrar("InputCheckbox").props.checked, true);
  assert.doesNotMatch(elementText(c.h.tree), /Pendência nos Alertas/);
});

test("cancelar e mesmo estado nao gravam; erro preserva o motivo e a selecao", async () => {
  const c = preparar({ salvar: async () => false });
  await c.selecionar("nao_identificado");
  await c.escrever("Falta comprovante");
  await c.confirmar();
  assert.equal(c.encontrar("InputTextoLongo").props.value, "Falta comprovante");
  assert.match(c.encontrar("InputTextoLongo").props.error, /confirmar a gravação/);
  await c.h.act(() => c.encontrar("BotaoCancelar").props.onClick());
  assert.equal(c.encontrar("InputTextoLongo"), undefined);
  const existente = preparar({ registro: item("identificado") });
  await existente.selecionar("identificado");
  assert.equal(existente.encontrar("InputTextoLongo"), undefined);
  assert.equal(existente.gravacoes.length, 0);
});

test("duplo clique gera um POST e mudanca concorrente exige revisao explicita, sem perder motivo", async () => {
  let concluir;
  const pendente = new Promise((resolve) => {
    concluir = resolve;
  });
  const c = preparar({ salvar: () => pendente });
  await c.selecionar("identificado");
  await c.escrever("Extrato conferido");
  const confirmar = c.encontrar("BotaoSalva").props.onClick;
  const primeira = confirmar();
  assert.equal(await confirmar(), undefined);
  assert.equal(c.gravacoes.length, 1);
  concluir(false);
  await primeira;
  await c.h.settle();
  await c.h.update({ item: item("nao_identificado", { registro_id: 10 }) });
  assert.equal(c.encontrar("InputTextoLongo").props.value, "Extrato conferido");
  assert.equal(c.encontrar("BotaoSalva"), undefined);
  assert.match(elementText(c.h.tree), /Pix foi atualizado/);
  await c.h.act(() => c.botao("Revisar com os dados atuais").props.onClick());
  assert.ok(c.encontrar("BotaoSalva"));
  assert.equal(c.gravacoes.length, 1);
});

test("estado salvo e historico sao somente leitura, sem misturar com OK e divergencia", async () => {
  const c = preparar({
    registro: item("identificado", {
      historico: [
        {
          id: 9,
          estado: "nao_identificado",
          justificativa: "Sem comprovante",
          usuario_nome: "Ana",
          data: "2026-10-22T10:00:00Z",
        },
        {
          id: 10,
          estado: "identificado",
          justificativa: "Crédito encontrado",
          usuario_nome: "Lucas",
          data: "2026-10-22T11:00:00Z",
        },
      ],
    }),
  });
  assert.doesNotMatch(elementText(c.h.tree), /Sem comprovante/);
  await c.h.act(() => c.botao("Histórico do Pix").props.onClick());
  assert.match(elementText(c.h.tree), /Sem comprovante/);
  assert.match(elementText(c.h.tree), /Crédito encontrado/);
  assert.equal(c.gravacoes.length, 0);
  assert.doesNotMatch(elementText(c.h.tree), /OK — conferido|Com divergência/);
});
