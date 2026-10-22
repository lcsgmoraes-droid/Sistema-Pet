import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const registro = (extra = {}) => ({
  id: 42,
  assinatura: "a".repeat(64),
  estado_conferencia: "pendente",
  ...extra,
});

function preparar({ item = registro(), props = {}, salvar = async () => true } = {}) {
  const gravacoes = [];
  const abertas = [];
  const componentes = [
    "BotaoCancelar",
    "BotaoInteracao",
    "BotaoSalva",
    "InputRadio",
    "InputTextoLongo",
  ];
  const mocks = new Map(
    componentes.map((nome) => [`../v2/${nome}/${nome}`, { __esModule: true, default: nome }]),
  );
  mocks.set("lucide-react", {
    AlertCircle: "AlertCircle",
    CheckCircle2: "CheckCircle2",
    Clock: "Clock",
    ExternalLink: "ExternalLink",
  });
  const harness = createControllerHarness(
    fileURLToPath(new URL("./ConferenciaCaixaItem.jsx", import.meta.url)),
    {
      mocks,
      props: {
        item,
        tipo: "pagamento",
        vendaId: 100,
        onSalvar: (...argumentos) => {
          gravacoes.push(argumentos);
          return salvar(...argumentos);
        },
        onAbrirVenda: (id) => abertas.push(id),
        ...props,
      },
    },
  );
  const encontrar = (tipo) => elements(harness.tree).find((node) => node.type === tipo);
  const situacao = () =>
    elements(harness.tree).find((node) => node.type === "p" && node.props.role === "status");
  return { harness, gravacoes, abertas, encontrar, situacao };
}

test("mostra os três estados do servidor sem marcar opção nem salvar automaticamente", async (t) => {
  for (const [estado, rotulo, cor] of [
    ["pendente", "Pendente", "slate"],
    ["ok", "OK — conferido", "emerald"],
    ["divergencia", "Com divergência", "red"],
  ]) {
    await t.test(estado, async () => {
      const env = preparar({ item: registro({ estado_conferencia: estado }) });
      await env.harness.settle();
      assert.equal(elementText(env.situacao()).trim(), rotulo);
      assert.match(env.harness.tree.props.className, new RegExp(`border-${cor}-`));
      assert.equal(env.encontrar("InputRadio").props.value, "");
      assert.equal(env.encontrar("InputRadio").props.opcoes.length, 3);
      assert.equal(env.encontrar("InputTextoLongo"), undefined);
      assert.deepEqual(env.gravacoes, []);
    });
  }
});

test("selecionar estado cria rascunho sem antecipar o estado salvo", async () => {
  const env = preparar();
  const nomeRadio = env.encontrar("InputRadio").props.name;
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("ok"));
  assert.equal(env.encontrar("InputRadio").props.name, nomeRadio);
  assert.equal(env.encontrar("InputRadio").props.value, "ok");
  assert.equal(env.encontrar("InputTextoLongo").props.required, false);
  assert.match(elementText(env.harness.tree), /Alteração ainda não salva/);
  assert.equal(elementText(env.situacao()).trim(), "Pendente");
  assert.deepEqual(env.gravacoes, []);
});

test("divergência exige motivo, apresenta erro, foca o campo e só envia nota preenchida", async () => {
  const item = registro();
  const env = preparar({ item });
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
  const campo = env.encontrar("InputTextoLongo");
  assert.equal(campo.props.label, "Motivo da divergência");
  assert.equal(campo.props.required, true);
  let focos = 0;
  campo.props.ref.current = {
    focus: () => {
      focos += 1;
    },
  };
  await env.harness.act(() => campo.props.onChange("  \n  "));
  await env.harness.act(() => env.encontrar("BotaoSalva").props.onClick());
  assert.equal(focos, 1);
  assert.match(env.encontrar("InputTextoLongo").props.error, /Descreva a divergência/);
  assert.deepEqual(env.gravacoes, []);
  await env.harness.act(() =>
    env.encontrar("InputTextoLongo").props.onChange("  Falta R$ 10,00.  "),
  );
  assert.equal(env.encontrar("InputTextoLongo").props.error, "");
  await env.harness.act(() => env.encontrar("BotaoSalva").props.onClick());
  assert.deepEqual(env.gravacoes, [["pagamento", item, "divergencia", "Falta R$ 10,00."]]);
  assert.equal(env.encontrar("InputTextoLongo"), undefined);
});

test("retorno false ou indefinido preserva escolha e observação para nova tentativa", async (t) => {
  for (const retorno of [false, undefined]) {
    await t.test(String(retorno), async () => {
      const env = preparar({ salvar: async () => retorno });
      await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
      await env.harness.act(() =>
        env.encontrar("InputTextoLongo").props.onChange("Verificar NSU."),
      );
      await env.harness.act(() => env.encontrar("BotaoSalva").props.onClick());
      assert.equal(env.gravacoes.length, 1);
      assert.equal(env.encontrar("InputRadio").props.value, "divergencia");
      assert.equal(env.encontrar("InputTextoLongo").props.value, "Verificar NSU.");
      assert.equal(env.encontrar("BotaoSalva").props.disabled, false);
      assert.equal(env.encontrar("BotaoSalva").props.loading, false);
      assert.equal(elementText(env.situacao()).trim(), "Pendente");
    });
  }
});

test("falha apresenta mensagem e mantém rascunho; sucesso posterior fecha a edição", async () => {
  let falhar = true;
  const env = preparar({
    salvar: async () => {
      if (falhar) throw { response: { data: { detail: "O lançamento mudou. Atualize o caixa." } } };
      return true;
    },
  });
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("ok"));
  await env.harness.act(() =>
    env.encontrar("InputTextoLongo").props.onChange("Conferido no extrato."),
  );
  await env.harness.act(() => env.encontrar("BotaoSalva").props.onClick());
  assert.equal(env.encontrar("InputTextoLongo").props.value, "Conferido no extrato.");
  assert.match(env.encontrar("InputTextoLongo").props.error, /O lançamento mudou/);
  falhar = false;
  await env.harness.act(() => env.encontrar("BotaoSalva").props.onClick());
  assert.equal(env.gravacoes.length, 2);
  assert.equal(env.encontrar("InputTextoLongo"), undefined);
  assert.equal(env.encontrar("InputRadio").props.value, "");
});

test("salvamento verdadeiro usa o estado atualizado pelo servidor e fecha apenas o rascunho salvo", async () => {
  const item = registro();
  let env;
  env = preparar({
    item,
    salvar: async (_, original, estado, observacao) => {
      assert.equal(original, item);
      await env.harness.update({
        item: registro({
          estado_conferencia: estado,
          conferencia: { usuario_nome: "Lucas", data: "2026-10-22T15:20:00Z", observacao },
        }),
      });
      return true;
    },
  });
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("ok"));
  await env.harness.act(() => env.encontrar("InputTextoLongo").props.onChange("Valor correto."));
  await env.harness.act(() => env.encontrar("BotaoSalva").props.onClick());
  assert.equal(env.encontrar("InputTextoLongo"), undefined);
  assert.equal(elementText(env.situacao()).trim(), "OK — conferido");
  assert.match(elementText(env.harness.tree), /Lucas/);
  assert.match(elementText(env.harness.tree), /22\/10\/2026.*12:20/);
  assert.match(elementText(env.harness.tree), /Valor correto\./);
});

test("duplo clique envia uma vez e mantém controles bloqueados enquanto aguarda resposta", async () => {
  let concluir;
  const env = preparar({
    salvar: () =>
      new Promise((resolve) => {
        concluir = resolve;
      }),
  });
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("ok"));
  const confirmar = env.encontrar("BotaoSalva").props.onClick;
  const primeiro = confirmar();
  const segundo = confirmar();
  await env.harness.settle();
  assert.equal(env.gravacoes.length, 1);
  assert.equal(env.harness.tree.props["aria-busy"], true);
  assert.equal(env.encontrar("InputRadio").props.disabled, true);
  assert.equal(env.encontrar("BotaoSalva").props.loading, true);
  assert.equal(env.encontrar("BotaoCancelar").props.disabled, true);
  concluir(false);
  await Promise.all([primeiro, segundo]);
  await env.harness.settle();
  assert.equal(env.harness.tree.props["aria-busy"], false);
  assert.equal(env.encontrar("InputRadio").props.value, "ok");
});

test("metadados ausentes, tipo inválido e bloqueio impedem iniciar uma conferência", async (t) => {
  for (const props of [
    { item: null },
    { item: registro({ id: 0 }) },
    { item: registro({ assinatura: null }) },
    { item: registro({ assinatura: "curta" }) },
    { tipo: "recebimento" },
    { bloqueado: true },
    { salvando: true },
    { onSalvar: undefined },
  ]) {
    await t.test(JSON.stringify(props), async () => {
      const env = preparar({ props });
      assert.equal(env.encontrar("InputRadio").props.disabled, true);
      await env.harness.act(() => env.encontrar("InputRadio").props.onChange("ok"));
      assert.equal(env.encontrar("InputTextoLongo"), undefined);
      assert.deepEqual(env.gravacoes, []);
    });
  }
});

test("bloqueio durante atualização conserva rascunho e impede enviar assinatura antiga", async () => {
  const env = preparar();
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("ok"));
  await env.harness.act(() =>
    env.encontrar("InputTextoLongo").props.onChange("Conferência iniciada."),
  );
  await env.harness.update({ bloqueado: true });
  assert.equal(env.encontrar("InputTextoLongo").props.disabled, true);
  await env.harness.act(() => env.encontrar("BotaoSalva").props.onClick());
  assert.deepEqual(env.gravacoes, []);
  const atualizado = registro({ assinatura: "b".repeat(64), conferencia_alterada: true });
  await env.harness.update({ bloqueado: false, item: atualizado });
  assert.equal(env.encontrar("InputTextoLongo").props.value, "Conferência iniciada.");
  assert.match(elementText(env.harness.tree), /Confira novamente este lançamento/);
  assert.deepEqual(
    env.gravacoes,
    [],
    "atualizar o item não reaplica a conferência automaticamente",
  );
  await env.harness.act(() => env.encontrar("BotaoSalva").props.onClick());
  assert.equal(env.gravacoes[0][1], atualizado);
});

test("abrir venda chama apenas a navegação e preserva a divergência ainda não salva", async () => {
  const env = preparar({ props: { vendaId: "100" } });
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
  await env.harness.act(() =>
    env.encontrar("InputTextoLongo").props.onChange("Comparar com a venda."),
  );
  await env.harness.act(() => env.encontrar("BotaoInteracao").props.onClick());
  assert.deepEqual(env.abertas, [100]);
  assert.deepEqual(env.gravacoes, []);
  assert.equal(env.encontrar("InputRadio").props.value, "divergencia");
  assert.equal(env.encontrar("InputTextoLongo").props.value, "Comparar com a venda.");
});

test("sem venda válida não há ação de abrir; cancelar elimina apenas a edição", async () => {
  const env = preparar({ item: registro({ estado_conferencia: "ok" }), props: { vendaId: null } });
  assert.equal(env.encontrar("BotaoInteracao"), undefined);
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("pendente"));
  await env.harness.act(() => env.encontrar("BotaoCancelar").props.onClick());
  assert.equal(env.encontrar("InputTextoLongo"), undefined);
  assert.equal(elementText(env.situacao()).trim(), "OK — conferido");
  assert.deepEqual(env.gravacoes, []);
});

test("trocar de lançamento não reaproveita o motivo do anterior", async () => {
  const env = preparar();
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
  await env.harness.act(() =>
    env.encontrar("InputTextoLongo").props.onChange("Rascunho do pagamento 42."),
  );
  await env.harness.update({ item: registro({ id: 43 }) });
  assert.equal(env.encontrar("InputTextoLongo"), undefined);
  assert.equal(env.encontrar("InputRadio").props.value, "");
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
  assert.equal(env.encontrar("InputTextoLongo").props.value, "");
  assert.deepEqual(env.gravacoes, []);
});
