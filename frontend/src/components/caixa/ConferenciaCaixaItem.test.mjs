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

test("OK e pendente salvam no clique sem formulário, confirmação extra ou nota antiga", async (t) => {
  for (const estado of ["ok", "pendente"]) {
    await t.test(estado, async () => {
      const item = registro({
        estado_conferencia: "divergencia",
        conferencia: { observacao: "Crédito foi lançado como débito." },
      });
      const env = preparar({ item });
      const nomeRadio = env.encontrar("InputRadio").props.name;
      await env.harness.act(() => env.encontrar("InputRadio").props.onChange(estado));
      assert.deepEqual(env.gravacoes, [["pagamento", item, estado, ""]]);
      assert.equal(env.encontrar("InputRadio").props.name, nomeRadio);
      assert.equal(env.encontrar("InputTextoLongo"), undefined);
      assert.equal(env.encontrar("BotaoSalva"), undefined);
      assert.equal(env.encontrar("BotaoCancelar"), undefined);
      assert.equal(elementText(env.situacao()).trim(), "Com divergência");
    });
  }
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
      assert.match(env.encontrar("InputTextoLongo").props.error, /confirmar a gravação/);
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
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
  await env.harness.act(() =>
    env.encontrar("InputTextoLongo").props.onChange("Forma de pagamento incorreta."),
  );
  await env.harness.act(() => env.encontrar("BotaoSalva").props.onClick());
  assert.equal(env.encontrar("InputTextoLongo").props.value, "Forma de pagamento incorreta.");
  assert.match(env.encontrar("InputTextoLongo").props.error, /O lançamento mudou/);
  falhar = false;
  await env.harness.act(() => env.encontrar("BotaoSalva").props.onClick());
  assert.equal(env.gravacoes.length, 2);
  assert.equal(env.encontrar("InputTextoLongo"), undefined);
  assert.equal(env.encontrar("InputRadio").props.value, "");
});

test("OK só muda após leitura do servidor e dispensa histórico de acerto na interface", async () => {
  const item = registro();
  let env;
  env = preparar({
    item,
    salvar: async (_, original, estado, observacao) => {
      assert.equal(original, item);
      await env.harness.update({
        item: registro({
          estado_conferencia: estado,
          conferencia: {
            usuario_nome: "Lucas",
            data: "2026-10-22T15:20:00Z",
            observacao: observacao || "Observação antiga que não deve aparecer.",
          },
        }),
      });
      return true;
    },
  });
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("ok"));
  assert.deepEqual(env.gravacoes, [["pagamento", item, "ok", ""]]);
  assert.equal(env.encontrar("InputTextoLongo"), undefined);
  assert.equal(elementText(env.situacao()).trim(), "OK — conferido");
  assert.doesNotMatch(elementText(env.harness.tree), /Último registro|Lucas|Observação antiga/);
});

test("duplo clique em OK envia uma vez e bloqueia as opções sem antecipar a cor", async () => {
  let concluir;
  const env = preparar({
    salvar: () =>
      new Promise((resolve) => {
        concluir = resolve;
      }),
  });
  const selecionar = env.encontrar("InputRadio").props.onChange;
  const primeiro = selecionar("ok");
  const segundo = selecionar("ok");
  await selecionar("divergencia");
  await env.harness.settle();
  assert.equal(env.gravacoes.length, 1);
  assert.equal(env.harness.tree.props["aria-busy"], true);
  assert.equal(env.encontrar("InputRadio").props.disabled, true);
  assert.equal(env.encontrar("BotaoSalva"), undefined);
  assert.equal(env.encontrar("InputTextoLongo"), undefined);
  assert.match(elementText(env.harness.tree), /Salvando conferência/);
  assert.equal(elementText(env.situacao()).trim(), "Pendente");
  concluir(false);
  await Promise.all([primeiro, segundo]);
  await env.harness.settle();
  assert.equal(env.harness.tree.props["aria-busy"], false);
  assert.equal(env.encontrar("InputRadio").props.value, "");
  assert.match(elementText(env.harness.tree), /confirmar a gravação/);
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

test("bloqueio durante atualização conserva divergência e impede enviar assinatura antiga", async () => {
  const env = preparar();
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
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
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
  await env.harness.act(() => env.encontrar("BotaoCancelar").props.onClick());
  assert.equal(env.encontrar("InputTextoLongo"), undefined);
  assert.equal(elementText(env.situacao()).trim(), "OK — conferido");
  assert.deepEqual(env.gravacoes, []);
});

test("falha ao clicar OK ou pendente mostra erro e exige novo clique consciente", async (t) => {
  for (const estado of ["ok", "pendente"]) {
    for (const retorno of [false, undefined, "erro"]) {
      await t.test(`${estado}: ${retorno}`, async () => {
        const item = registro({ estado_conferencia: "divergencia" });
        let falhar = true;
        const env = preparar({
          item,
          salvar: async () => {
            if (!falhar) return true;
            if (retorno === "erro") throw new Error("Servidor indisponível.");
            return retorno;
          },
        });
        await env.harness.act(() => env.encontrar("InputRadio").props.onChange(estado));
        assert.equal(env.gravacoes.length, 1);
        assert.equal(elementText(env.situacao()).trim(), "Com divergência");
        assert.match(env.harness.tree.props.className, /border-red-/);
        const alerta = elements(env.harness.tree).find((node) => node.props?.role === "alert");
        assert.match(elementText(alerta), /Servidor indisponível|confirmar a gravação/);
        assert.equal(env.encontrar("InputRadio").props.disabled, false);
        assert.equal(env.encontrar("InputTextoLongo"), undefined);
        falhar = false;
        await env.harness.settle();
        assert.equal(env.gravacoes.length, 1, "nenhuma tentativa automática após a falha");
        await env.harness.act(() => env.encontrar("InputRadio").props.onChange(estado));
        assert.equal(env.gravacoes.length, 2);
        assert.equal(
          elements(env.harness.tree).find((node) => node.props?.role === "alert"),
          undefined,
        );
      });
    }
  }
});

test("trocar rascunho de divergência por OK não grava a justificativa ainda não salva", async () => {
  const item = registro();
  const env = preparar({ item });
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
  await env.harness.act(() =>
    env.encontrar("InputTextoLongo").props.onChange("Rascunho que foi descartado."),
  );
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("ok"));
  assert.deepEqual(env.gravacoes, [["pagamento", item, "ok", ""]]);
  assert.equal(env.encontrar("InputTextoLongo"), undefined);
  assert.equal(env.encontrar("BotaoSalva"), undefined);
});

test("somente divergência mostra motivo, responsável e horário; demais estados não herdam nota", async (t) => {
  for (const estado of ["pendente", "ok", "divergencia"]) {
    await t.test(estado, async () => {
      const env = preparar({
        item: registro({
          estado_conferencia: estado,
          conferencia: {
            usuario_nome: "Lucas",
            data: "2026-10-22T15:20:00Z",
            observacao: "Crédito lançado como débito.",
          },
        }),
      });
      const texto = elementText(env.harness.tree);
      if (estado === "divergencia") {
        assert.match(texto, /Último registro:.*Lucas/);
        assert.match(texto, /22\/10\/2026.*12:20/);
        assert.match(texto, /Crédito lançado como débito/);
      } else {
        assert.doesNotMatch(texto, /Último registro|Lucas|Crédito lançado como débito/);
      }
      await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
      assert.equal(
        env.encontrar("InputTextoLongo").props.value,
        estado === "divergencia" ? "Crédito lançado como débito." : "",
      );
    });
  }
});

test("dupla confirmação de divergência não duplica o registro e preserva o motivo na falha", async () => {
  let concluir;
  const env = preparar({
    salvar: () =>
      new Promise((resolve) => {
        concluir = resolve;
      }),
  });
  await env.harness.act(() => env.encontrar("InputRadio").props.onChange("divergencia"));
  await env.harness.act(() => env.encontrar("InputTextoLongo").props.onChange("Corrigir forma."));
  const confirmar = env.encontrar("BotaoSalva").props.onClick;
  const primeiro = confirmar();
  const segundo = confirmar();
  await env.harness.settle();
  assert.equal(env.gravacoes.length, 1);
  assert.equal(env.encontrar("BotaoSalva").props.loading, true);
  assert.equal(env.encontrar("BotaoCancelar").props.disabled, true);
  concluir(false);
  await Promise.all([primeiro, segundo]);
  await env.harness.settle();
  assert.equal(env.encontrar("InputTextoLongo").props.value, "Corrigir forma.");
  assert.equal(env.encontrar("BotaoSalva").props.loading, false);
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
