import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { salvarIfoodConfiguracao } from "../../api/ifood";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import InputCheck from "../v2/InputCheck/InputCheck";
import InputMoeda from "../v2/InputMoeda/InputMoeda";
import InputPercentual from "../v2/InputPercentual/InputPercentual";
import InputTexto from "../v2/InputTexto/InputTexto";
import { mensagemErroIfood, valorConhecido } from "./ifoodPresentation";

const CUSTOS = [
  { key: "commission_merchant_percent", label: "Comissão · entrega própria" },
  { key: "commission_ifood_percent", label: "Comissão · entrega iFood" },
  { key: "payment_fee_percent", label: "Taxa de pagamento" },
  { key: "tax_percent", label: "Tributos estimados" },
  { key: "additional_unit_cost", label: "Despesa adicional por unidade", moeda: true },
  { key: "target_margin_percent", label: "Meta de contribuição", max: 99.99 },
];

function assinaturaRegras(config) {
  return JSON.stringify([
    config.default_markup_percent ?? 0,
    config.stock_safety ?? 0,
    ...CUSTOS.map(({ key }) => config[key] ?? null),
  ]);
}

function CustoOpcional({ campo, disabled, onChange, value }) {
  const conhecido = valorConhecido(value);
  const CampoValor = campo.moeda ? InputMoeda : InputPercentual;
  return (
    <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
      <div className="flex items-start justify-between gap-3">
        <p className="v2-texto font-medium">{campo.label}</p>
        <InputCheck
          id={`ifood-custo-${campo.key}`}
          checked={conhecido}
          disabled={disabled}
          label={conhecido ? "Informado" : "Definir valor"}
          onChange={(checked) => onChange(checked ? 0 : null)}
        />
      </div>
      {conhecido ? (
        <CampoValor
          id={`ifood-valor-${campo.key}`}
          label={campo.label}
          disabled={disabled}
          value={value}
          onChange={onChange}
          maxValue={campo.max}
          help="Zero confirma que este custo não se aplica."
        />
      ) : (
        <p className="v2-texto-ajuda mt-2">Não informado</p>
      )}
    </div>
  );
}

export default function IfoodConfiguracao({ config, onSalvo, podeConfigurar }) {
  // Sem rascunho, novas consultas atualizam o formulario. Com rascunho, uma
  // atualizacao externa e apresentada antes de sobrescrever qualquer valor.
  const [rascunho, setRascunho] = useState(null);
  const form = rascunho?.valores || config;
  const conflito = Boolean(rascunho && rascunho.origem !== assinaturaRegras(config));
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const atualizar = (campo, valor) => {
    setRascunho((atual) => ({
      origem: atual?.origem || assinaturaRegras(config),
      valores: { ...(atual?.valores || config), [campo]: valor },
    }));
    setSucesso("");
  };

  async function salvar(evento) {
    evento.preventDefault();
    if (salvando || !podeConfigurar || conflito) return;
    const estoque = Number(String(form.stock_safety ?? 0).replace(",", "."));
    if (!Number.isFinite(estoque) || estoque < 0 || estoque > 1000000) {
      setErro("Informe uma reserva de segurança entre 0 e 1.000.000.");
      return;
    }
    setSalvando(true);
    setErro("");
    setSucesso("");
    try {
      const payload = {
        default_markup_percent: Number(form.default_markup_percent ?? 0),
        stock_safety: estoque,
        ...Object.fromEntries(CUSTOS.map(({ key }) => [key, form[key] ?? null])),
      };
      const response = await salvarIfoodConfiguracao(payload);
      onSalvo(response.data.config);
      setRascunho(null);
      setSucesso("Regras salvas. Os preços e as estimativas serão recalculados no catálogo.");
    } catch (error) {
      setErro(mensagemErroIfood(error, "Não foi possível salvar as regras do iFood."));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-5">
      <div>
        <h2 className="v2-titulo-secao">Regras desta loja</h2>
        <p className="v2-texto-ajuda mt-1">
          Informe as condições do contrato da loja. Custos desconhecidos ficam sem valor; os
          cenários de entrega servem somente para simular a contribuição por unidade.
        </p>
      </div>
      {!podeConfigurar ? (
        <p role="status" className="v2-texto text-amber-700 dark:text-amber-300">
          Seu acesso permite consultar. Para alterar estas regras, é necessária permissão de editar
          configurações.
        </p>
      ) : null}
      {conflito ? (
        <div
          role="alert"
          className="space-y-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200"
        >
          <p>
            As regras da loja foram atualizadas enquanto você editava. Seu rascunho foi preservado.
            Recarregue os valores atuais antes de salvar; isso descarta apenas este rascunho.
          </p>
          <BotaoInteracao
            icon={RefreshCw}
            tamanho="pequeno"
            disabled={salvando}
            onClick={() => {
              setRascunho(null);
              setErro("");
              setSucesso("");
            }}
          >
            Recarregar regras atuais
          </BotaoInteracao>
        </div>
      ) : null}
      <div className="grid gap-4 md:grid-cols-2">
        <InputPercentual
          id="ifood-acrescimo-geral"
          label="Acréscimo sobre o preço normal do ERP"
          maxValue={300}
          disabled={!podeConfigurar || salvando}
          value={form.default_markup_percent ?? 0}
          onChange={(valor) => atualizar("default_markup_percent", valor)}
          help="Usado quando o produto não tem preço específico para o iFood."
        />
        <InputTexto
          id="ifood-estoque-seguranca"
          label="Reserva de segurança de estoque"
          inputMode="decimal"
          disabled={!podeConfigurar || salvando}
          value={String(form.stock_safety ?? 0).replace(".", ",")}
          onChange={(valor) => {
            if (/^[0-9]*[.,]?[0-9]*$/.test(valor)) atualizar("stock_safety", valor);
          }}
          help="Quantidade descontada do estoque livre, depois das reservas existentes."
        />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {CUSTOS.map((campo) => (
          <CustoOpcional
            key={campo.key}
            campo={campo}
            disabled={!podeConfigurar || salvando}
            value={form[campo.key]}
            onChange={(valor) => atualizar(campo.key, valor)}
          />
        ))}
      </div>
      <p className="v2-texto-ajuda">
        As taxas percentuais desta simulação incidem sobre o preço vigente do item. Entrega,
        embalagem por pedido, descontos financiados e mensalidade devem ser considerados na análise
        do pedido e do período. A meta gera um aviso e não bloqueia o cadastro.
      </p>
      {erro ? (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {erro}
        </p>
      ) : null}
      {sucesso ? (
        <p role="status" className="text-sm text-emerald-700 dark:text-emerald-300">
          {sucesso}
        </p>
      ) : null}
      <BotaoSalva loading={salvando} disabled={!podeConfigurar || conflito}>
        Salvar regras da loja
      </BotaoSalva>
    </form>
  );
}
